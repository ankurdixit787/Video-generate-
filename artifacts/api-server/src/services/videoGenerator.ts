import ffmpeg from "fluent-ffmpeg";
import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import { logger } from "../lib/logger";
import { searchImages, downloadImage } from "./imageSearch";
import { generateTTS, getAudioDuration } from "./tts";

export interface VideoJob {
  id: string;
  text: string;
  status: "pending" | "processing" | "done" | "failed";
  outputPath?: string;
  error?: string;
}

const TARGET_DURATION = 60;
const FPS = 25;
const jobs = new Map<string, VideoJob>();

function tmpDir(): string {
  const dir = path.resolve(process.cwd(), "tmp");
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function getJob(id: string): VideoJob | undefined {
  return jobs.get(id);
}

export async function createVideoJob(text: string): Promise<string> {
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const job: VideoJob = { id, text, status: "pending" };
  jobs.set(id, job);
  processJob(job).catch((err) => {
    job.status = "failed";
    job.error = err.message;
    logger.error({ err: err.message, id }, "Video job failed");
  });
  return id;
}

async function processJob(job: VideoJob): Promise<void> {
  job.status = "processing";
  logger.info({ id: job.id }, "Starting video job");

  const dir = path.join(tmpDir(), job.id);
  fs.mkdirSync(dir, { recursive: true });

  try {
    const chunks = splitTextIntoChunks(job.text);
    logger.info({ chunks: chunks.length }, "Text split into chunks");

    interface ChunkData {
      text: string;
      audioPath: string;
      imagePath: string;
      duration: number;
    }

    const chunkData: ChunkData[] = [];

    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i]!;
      const audioPath = path.join(dir, `audio_${i}.mp3`);

      logger.info({ chunk: chunk.slice(0, 50), i }, "Generating TTS for chunk");
      const dur = await generateTTS(chunk, audioPath);
      logger.info({ dur, i }, "TTS duration for chunk");

      const keywords = extractKeywords(chunk);
      logger.info({ keywords, i }, "Searching image");
      const urls = await searchImages(keywords, 1);
      const imgPath = path.join(dir, `img_${i}.jpg`);

      if (urls.length > 0) {
        try {
          await downloadImage(urls[0]!, imgPath);
          if (!fs.existsSync(imgPath) || fs.statSync(imgPath).size < 500) throw new Error("Image too small");
        } catch {
          logger.warn({ i }, "Image download failed, using fallback");
          await createBhaktiFallbackImage(imgPath, chunk, i);
        }
      } else {
        await createBhaktiFallbackImage(imgPath, chunk, i);
      }

      chunkData.push({ text: chunk, audioPath, imagePath: imgPath, duration: dur });
    }

    const totalRawDuration = chunkData.reduce((s, c) => s + c.duration, 0);
    logger.info({ totalRawDuration, TARGET_DURATION }, "Total raw audio duration");

    const speedFactor = totalRawDuration / TARGET_DURATION;
    const adjustedChunks = chunkData.map((c) => ({
      ...c,
      adjustedDuration: c.duration / speedFactor,
    }));

    const segmentVideos: string[] = [];

    for (let i = 0; i < adjustedChunks.length; i++) {
      const chunk = adjustedChunks[i]!;
      const segPath = path.join(dir, `seg_${i}.mp4`);
      const safeText = chunk.text.replace(/['"\\:]/g, "").replace(/\n/g, " ").slice(0, 55);
      const frames = Math.ceil(chunk.adjustedDuration * FPS);

      const zoomEffect = i % 3 === 0
        ? `zoompan=z='min(zoom+0.001,1.3)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`
        : i % 3 === 1
        ? `zoompan=z='if(eq(on\\,1)\\,1.3\\,max(1\\,zoom-0.001))':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`
        : `zoompan=z='min(zoom+0.0008,1.2)':d=${frames}:x='if(eq(on\\,1)\\,0\\,x+0.5)':y='ih/2-(ih/zoom/2)'`;

      const paddedAudio = path.join(dir, `padded_audio_${i}.mp3`);
      await padOrTrimAudio(chunk.audioPath, paddedAudio, chunk.adjustedDuration);

      await new Promise<void>((resolve, reject) => {
        ffmpeg(chunk.imagePath)
          .inputOptions(["-loop", "1"])
          .input(paddedAudio)
          .complexFilter([
            `[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,` +
            `${zoomEffect}:s=1280x720:fps=${FPS},` +
            `drawtext=text='${safeText}':fontcolor=white:fontsize=28:x=20:y=h-th-25:` +
            `box=1:boxcolor=black@0.6:boxborderw=8,` +
            `fade=t=in:st=0:d=0.5,fade=t=out:st=${Math.max(0, chunk.adjustedDuration - 0.5)}:d=0.5[v]`,
          ])
          .outputOptions([
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", String(FPS),
            "-t", String(chunk.adjustedDuration),
          ])
          .output(segPath)
          .on("end", () => resolve())
          .on("error", (err: Error) => reject(err))
          .run();
      });

      segmentVideos.push(segPath);
      logger.info({ i, dur: chunk.adjustedDuration }, "Segment created");
    }

    const concatList = path.join(dir, "concat.txt");
    fs.writeFileSync(concatList, segmentVideos.map((p) => `file '${p}'`).join("\n"));

    const videoPath = path.join(dir, "output.mp4");
    await new Promise<void>((resolve, reject) => {
      ffmpeg()
        .input(concatList)
        .inputOptions(["-f", "concat", "-safe", "0"])
        .outputOptions([
          "-c:v", "libx264",
          "-c:a", "aac",
          "-movflags", "+faststart",
          "-pix_fmt", "yuv420p",
          "-t", String(TARGET_DURATION),
        ])
        .output(videoPath)
        .on("end", () => resolve())
        .on("error", (err: Error) => reject(err))
        .run();
    });

    try {
      segmentVideos.forEach((p) => { try { fs.unlinkSync(p); } catch {} });
      fs.unlinkSync(concatList);
    } catch {}

    const finalDur = getAudioDuration(videoPath);
    logger.info({ id: job.id, finalDur }, "Video completed");

    job.outputPath = videoPath;
    job.status = "done";
  } catch (err) {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
    throw err;
  }
}

function splitTextIntoChunks(text: string): string[] {
  const raw = text
    .split(/[।\.\!\?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 5);

  if (raw.length === 0) return [text];

  const chunks: string[] = [];
  let current = "";
  for (const s of raw) {
    if (current.length > 0 && (current + s).length > 100) {
      chunks.push(current.trim());
      current = s;
    } else {
      current = current ? current + ". " + s : s;
    }
  }
  if (current.trim().length > 5) chunks.push(current.trim());

  if (chunks.length < 3 && text.length > 100) {
    const words = text.split(/\s+/);
    const perChunk = Math.ceil(words.length / 4);
    const result: string[] = [];
    for (let i = 0; i < words.length; i += perChunk) {
      result.push(words.slice(i, i + perChunk).join(" "));
    }
    return result.filter((s) => s.length > 5);
  }

  return chunks.length > 0 ? chunks : [text];
}

function extractKeywords(text: string): string {
  const bhaktiMap: [string, string][] = [
    ["ram", "lord rama temple india ayodhya"],
    ["krishna", "lord krishna temple vrindavan mathura"],
    ["hanuman", "hanuman temple india devotional"],
    ["shiv", "shiva temple mahadev india"],
    ["durga", "durga mata temple navratri india"],
    ["ganesh", "ganesh temple india ganesha"],
    ["lakshmi", "lakshmi mata temple diwali india"],
    ["sai", "sai baba shirdi temple"],
    ["tirupati", "tirupati balaji temple india"],
    ["vaishno", "vaishno devi temple jammu"],
    ["kashi", "kashi vishwanath varanasi ganga"],
    ["jagannath", "jagannath puri temple"],
    ["kali", "kali mata temple india"],
    ["geeta", "bhagavad gita krishna arjuna"],
    ["guru", "spiritual guru india ashram"],
    ["mandir", "india temple devotional prayer"],
    ["bhakti", "india devotional temple worship"],
  ];

  const lower = text.toLowerCase();
  for (const [key, val] of bhaktiMap) {
    if (lower.includes(key)) return val;
  }
  return "india temple devotional spiritual prayer";
}

async function createBhaktiFallbackImage(outputPath: string, text: string, index: number): Promise<void> {
  const colors = ["0x1a0a00", "0x0a0a1a", "0x001a0a", "0x1a0a0a", "0x0a1a00"];
  const color = colors[index % colors.length]!;
  const safeText = text.replace(/['"\\:]/g, "").replace(/\n/g, " ").slice(0, 45);
  try {
    execSync(
      `ffmpeg -y -f lavfi -i "color=c=${color}:size=1280x720:rate=1" ` +
      `-vf "drawtext=text='🙏 Bhakti':fontcolor=gold:fontsize=60:x=(w-text_w)/2:y=h/3,` +
      `drawtext=text='${safeText}':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=2*h/3" ` +
      `-frames:v 1 "${outputPath}" 2>/dev/null`,
      { timeout: 15000 }
    );
  } catch {
    execSync(`ffmpeg -y -f lavfi -i "color=c=${color}:size=1280x720:rate=1" -frames:v 1 "${outputPath}" 2>/dev/null`, { timeout: 10000 });
  }
}

async function padOrTrimAudio(inputPath: string, outputPath: string, targetDur: number): Promise<void> {
  const actual = getAudioDuration(inputPath);
  if (Math.abs(actual - targetDur) < 0.2) {
    fs.copyFileSync(inputPath, outputPath);
    return;
  }
  if (actual < targetDur) {
    const pad = targetDur - actual;
    const silPath = outputPath + "_sil.mp3";
    execSync(`ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${pad}" -c:a libmp3lame "${silPath}" 2>/dev/null`, { timeout: 15000 });
    const lst = outputPath + ".lst";
    fs.writeFileSync(lst, `file '${inputPath}'\nfile '${silPath}'`);
    await new Promise<void>((resolve, reject) => {
      ffmpeg().input(lst).inputOptions(["-f", "concat", "-safe", "0"])
        .audioCodec("libmp3lame").output(outputPath)
        .on("end", () => { try { fs.unlinkSync(lst); fs.unlinkSync(silPath); } catch {} resolve(); })
        .on("error", (err: Error) => reject(err)).run();
    });
  } else {
    await new Promise<void>((resolve, reject) => {
      ffmpeg(inputPath).outputOptions(["-t", String(targetDur)]).audioCodec("libmp3lame")
        .output(outputPath).on("end", () => resolve()).on("error", (err: Error) => reject(err)).run();
    });
  }
}

export function cleanupJob(id: string): void {
  const job = jobs.get(id);
  if (job?.outputPath) {
    const dir = path.dirname(job.outputPath);
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
  jobs.delete(id);
}
