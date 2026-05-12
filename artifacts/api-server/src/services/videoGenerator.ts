import ffmpeg from "fluent-ffmpeg";
import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import { logger } from "../lib/logger";
import { searchImages, downloadImage } from "./imageSearch";
import { generateTTS, generateTTSFallback } from "./tts";

export interface VideoJob {
  id: string;
  text: string;
  status: "pending" | "processing" | "done" | "failed";
  outputPath?: string;
  error?: string;
}

const TARGET_DURATION = 60;
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
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
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
    const sentences = splitTextIntoChunks(job.text);
    logger.info({ chunks: sentences.length }, "Text split into chunks");

    const audioPaths: string[] = [];
    const imagePaths: string[] = [];

    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i]!;
      const audioPath = path.join(dir, `audio_${i}.mp3`);

      try {
        await generateTTS(sentence, audioPath);
        if (!fs.existsSync(audioPath) || fs.statSync(audioPath).size < 100) {
          throw new Error("TTS file too small");
        }
      } catch {
        logger.warn({ i }, "Primary TTS failed, using fallback");
        await generateTTSFallback(sentence, audioPath);
      }
      audioPaths.push(audioPath);

      const keywords = extractKeywords(sentence);
      logger.info({ keywords }, "Searching images");
      const imageUrls = await searchImages(keywords, 1);
      const imgPath = path.join(dir, `img_${i}.jpg`);

      if (imageUrls.length > 0) {
        try {
          await downloadImage(imageUrls[0]!, imgPath);
        } catch {
          await createFallbackImage(imgPath, sentence);
        }
      } else {
        await createFallbackImage(imgPath, sentence);
      }
      imagePaths.push(imgPath);
    }

    const mergedAudio = path.join(dir, "merged_audio.mp3");
    await mergeAudioFiles(audioPaths, mergedAudio);

    const rawDuration = getAudioDuration(mergedAudio);
    logger.info({ rawDuration, target: TARGET_DURATION }, "Audio duration");

    const paddedAudio = path.join(dir, "padded_audio.mp3");
    await padOrTrimAudio(mergedAudio, paddedAudio, TARGET_DURATION);

    const videoPath = path.join(dir, "output.mp4");
    await buildVideo(imagePaths, paddedAudio, TARGET_DURATION, job.text, videoPath);

    job.outputPath = videoPath;
    job.status = "done";
    logger.info({ id: job.id }, "Video job completed successfully");
  } catch (err) {
    fs.rmSync(dir, { recursive: true, force: true });
    throw err;
  }
}

function splitTextIntoChunks(text: string): string[] {
  const sentences = text
    .split(/[।\.\!\?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 3);

  if (sentences.length === 0) return [text];

  const chunks: string[] = [];
  let current = "";
  for (const s of sentences) {
    if ((current + " " + s).length > 120) {
      if (current) chunks.push(current.trim());
      current = s;
    } else {
      current = current ? current + ". " + s : s;
    }
  }
  if (current.trim()) chunks.push(current.trim());

  return chunks.length > 0 ? chunks : [text];
}

function extractKeywords(text: string): string {
  const stopWords = new Set([
    "hai", "hain", "ka", "ki", "ke", "ko", "se", "ne", "mein", "par", "aur",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "karo", "karna", "yeh", "woh", "main", "tum", "aap", "hum", "unka",
    "unki", "unke", "inka", "inki", "inke", "jaise", "waisa", "lekin",
  ]);
  const words = text
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .split(/\s+/)
    .filter((w) => w.length > 3 && !stopWords.has(w));

  const bhaktiTerms: Record<string, string> = {
    ram: "lord ram temple india",
    krishna: "lord krishna temple vrindavan",
    hanuman: "hanuman temple india",
    shiv: "shiva temple mahadev",
    durga: "durga mata temple",
    ganesh: "ganesh temple india",
    lakshmi: "lakshmi temple devi",
    kali: "kali mata temple",
    sai: "sai baba shirdi",
    tirupati: "tirupati balaji temple",
    vaishno: "vaishno devi temple",
    kashi: "kashi vishwanath temple varanasi",
    jagannath: "jagannath temple puri",
  };

  for (const [key, replacement] of Object.entries(bhaktiTerms)) {
    if (text.toLowerCase().includes(key)) {
      return replacement;
    }
  }

  return (words.slice(0, 3).join(" ") + " india temple devotional") || "hindu temple india devotional";
}

async function createFallbackImage(outputPath: string, text: string): Promise<void> {
  const safeText = text.replace(/['":\\]/g, "").slice(0, 40);
  try {
    execSync(
      `ffmpeg -y -f lavfi -i "color=c=0x1a0a00:size=1280x720:rate=1" ` +
      `-vf "drawtext=text='${safeText}':fontcolor=gold:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2" ` +
      `-frames:v 1 "${outputPath}" 2>/dev/null`,
      { timeout: 15000 }
    );
  } catch {
    execSync(`ffmpeg -y -f lavfi -i "color=c=0x1a0a00:size=1280x720:rate=1" -frames:v 1 "${outputPath}" 2>/dev/null`, { timeout: 10000 });
  }
}

function getAudioDuration(audioPath: string): number {
  try {
    const output = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${audioPath}"`,
      { timeout: 10000 }
    ).toString().trim();
    return parseFloat(output) || 30;
  } catch {
    return 30;
  }
}

async function padOrTrimAudio(inputPath: string, outputPath: string, targetDuration: number): Promise<void> {
  const actual = getAudioDuration(inputPath);
  logger.info({ actual, targetDuration }, "Adjusting audio to target duration");

  if (Math.abs(actual - targetDuration) < 1) {
    fs.copyFileSync(inputPath, outputPath);
    return;
  }

  if (actual < targetDuration) {
    const silence = targetDuration - actual;
    const silencePath = path.dirname(outputPath) + "/silence.mp3";
    execSync(`ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${silence}" -c:a libmp3lame "${silencePath}" 2>/dev/null`, { timeout: 15000 });

    const listFile = outputPath + ".txt";
    fs.writeFileSync(listFile, `file '${inputPath}'\nfile '${silencePath}'`);
    await new Promise<void>((resolve, reject) => {
      ffmpeg()
        .input(listFile)
        .inputOptions(["-f", "concat", "-safe", "0"])
        .audioCodec("libmp3lame")
        .output(outputPath)
        .on("end", () => resolve())
        .on("error", (err: Error) => reject(err))
        .run();
    });
    try { fs.unlinkSync(listFile); fs.unlinkSync(silencePath); } catch {}
  } else {
    await new Promise<void>((resolve, reject) => {
      ffmpeg(inputPath)
        .outputOptions(["-t", String(targetDuration)])
        .audioCodec("libmp3lame")
        .output(outputPath)
        .on("end", () => resolve())
        .on("error", (err: Error) => reject(err))
        .run();
    });
  }
}

async function mergeAudioFiles(audioPaths: string[], outputPath: string): Promise<void> {
  if (audioPaths.length === 1) {
    fs.copyFileSync(audioPaths[0]!, outputPath);
    return;
  }
  const listFile = outputPath + ".txt";
  fs.writeFileSync(listFile, audioPaths.map((p) => `file '${p}'`).join("\n"));
  await new Promise<void>((resolve, reject) => {
    ffmpeg()
      .input(listFile)
      .inputOptions(["-f", "concat", "-safe", "0"])
      .audioCodec("libmp3lame")
      .output(outputPath)
      .on("end", () => { try { fs.unlinkSync(listFile); } catch {} resolve(); })
      .on("error", (err: Error) => reject(err))
      .run();
  });
}

async function buildVideo(
  imagePaths: string[],
  audioPath: string,
  totalDuration: number,
  titleText: string,
  outputPath: string
): Promise<void> {
  const dir = path.dirname(outputPath);
  const perImageDuration = totalDuration / imagePaths.length;
  const frames = Math.ceil(perImageDuration * 25);

  const safeTitle = titleText
    .replace(/['"\\:]/g, "")
    .replace(/\n/g, " ")
    .slice(0, 50);

  const processedImages: string[] = [];
  for (let i = 0; i < imagePaths.length; i++) {
    const processedPath = path.join(dir, `proc_${i}.mp4`);
    const zoomDir = i % 2 === 0
      ? `zoompan=z='min(zoom+0.0008,1.25)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`
      : `zoompan=z='if(eq(on\\,1)\\,1.25\\,max(1\\,zoom-0.0008))':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`;

    await new Promise<void>((resolve, reject) => {
      ffmpeg(imagePaths[i]!)
        .inputOptions(["-loop", "1"])
        .complexFilter([
          `[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,` +
          `${zoomDir}:s=1280x720:fps=25,` +
          `drawtext=text='${safeTitle}':fontcolor=white:fontsize=26:x=20:y=h-th-20:` +
          `box=1:boxcolor=black@0.55:boxborderw=8[v]`,
        ])
        .outputOptions(["-map", "[v]", "-t", String(perImageDuration), "-r", "25", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast"])
        .output(processedPath)
        .on("end", () => resolve())
        .on("error", (err: Error) => reject(err))
        .run();
    });
    processedImages.push(processedPath);
  }

  const concatList = path.join(dir, "concat.txt");
  fs.writeFileSync(concatList, processedImages.map((p) => `file '${p}'`).join("\n"));

  const videoOnly = path.join(dir, "video_only.mp4");
  await new Promise<void>((resolve, reject) => {
    ffmpeg()
      .input(concatList)
      .inputOptions(["-f", "concat", "-safe", "0"])
      .outputOptions(["-c", "copy"])
      .output(videoOnly)
      .on("end", () => resolve())
      .on("error", (err: Error) => reject(err))
      .run();
  });

  await new Promise<void>((resolve, reject) => {
    ffmpeg(videoOnly)
      .input(audioPath)
      .outputOptions(["-c:v", "copy", "-c:a", "aac", "-t", String(totalDuration), "-shortest", "-movflags", "+faststart"])
      .output(outputPath)
      .on("end", () => resolve())
      .on("error", (err: Error) => reject(err))
      .run();
  });

  try {
    fs.unlinkSync(concatList);
    fs.unlinkSync(videoOnly);
    processedImages.forEach((p) => { try { fs.unlinkSync(p); } catch {} });
  } catch {}

  const finalDuration = getAudioDuration(outputPath);
  logger.info({ outputPath, finalDuration }, "Video built");
}

export function cleanupJob(id: string): void {
  const job = jobs.get(id);
  if (job?.outputPath) {
    const dir = path.dirname(job.outputPath);
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
  jobs.delete(id);
}
