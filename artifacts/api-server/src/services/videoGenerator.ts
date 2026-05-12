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

const TARGET_SEC = 60;
const FPS = 25;
const jobs = new Map<string, VideoJob>();

function workDir(id: string): string {
  const d = path.resolve(process.cwd(), "tmp", id);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

export function getJob(id: string): VideoJob | undefined { return jobs.get(id); }

export async function createVideoJob(text: string): Promise<string> {
  const id = `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
  const job: VideoJob = { id, text, status: "pending" };
  jobs.set(id, job);
  processJob(job).catch((err) => {
    job.status = "failed";
    job.error = String(err?.message ?? err);
    logger.error({ id, err: job.error }, "Job failed");
  });
  return id;
}

async function processJob(job: VideoJob): Promise<void> {
  job.status = "processing";
  const dir = workDir(job.id);
  logger.info({ id: job.id, dir }, "Job started");

  try {
    const chunks = splitText(job.text);
    logger.info({ chunks: chunks.length, texts: chunks.map(c => c.slice(0,30)) }, "Chunks ready");

    type Seg = { text: string; audio: string; img: string; rawDur: number };
    const segs: Seg[] = [];

    for (let i = 0; i < chunks.length; i++) {
      const text = chunks[i]!;
      const audio = path.join(dir, `a${i}.mp3`);
      const img   = path.join(dir, `i${i}.jpg`);

      logger.info({ i, text: text.slice(0,50) }, "Generating audio");
      const rawDur = await generateTTS(text, audio);
      logger.info({ i, rawDur }, "Audio done");

      logger.info({ i }, "Downloading image");
      const [imgUrl] = await searchImages(text, 1);
      try {
        await downloadImage(imgUrl!, img);
        const sz = fs.statSync(img).size;
        if (sz < 5000) throw new Error(`Image too small: ${sz}`);
        logger.info({ i, sz }, "Image downloaded");
      } catch (e: any) {
        logger.warn({ i, err: e.message }, "Image download failed – using generated bhakti image");
        await makeBhaktiImage(img, text, i);
      }

      segs.push({ text, audio, img, rawDur });
    }

    const totalRaw = segs.reduce((s, x) => s + x.rawDur, 0);
    const scale = totalRaw > 0 ? TARGET_SEC / totalRaw : 1;
    logger.info({ totalRaw, scale, TARGET_SEC }, "Audio scaling");

    const segVids: string[] = [];
    for (let i = 0; i < segs.length; i++) {
      const seg = segs[i]!;
      const dur = Math.max(2, seg.rawDur * scale);
      const segOut = path.join(dir, `seg${i}.mp4`);

      const paddedAudio = path.join(dir, `ap${i}.mp3`);
      await padAudio(seg.audio, paddedAudio, dur);

      const frames = Math.ceil(dur * FPS);
      const safeText = seg.text.replace(/['"\\:]/g, " ").replace(/\n/g, " ").slice(0, 60);
      const zoomExpr = [
        `zoompan=z='min(zoom+0.001,1.3)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`,
        `zoompan=z='if(lte(on\\,1)\\,1.3\\,max(1\\,zoom-0.001))':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`,
        `zoompan=z='1.15':d=${frames}:x='iw*0.05*on/${frames}':y='ih/2-(ih/zoom/2)'`,
      ][i % 3]!;

      logger.info({ i, dur, frames }, "Building segment");
      await runFFmpeg(
        [seg.img, paddedAudio],
        ["-loop", "1", "-t", String(dur)],
        [
          `[0:v]scale=1280:720:force_original_aspect_ratio=increase,` +
          `crop=1280:720,${zoomExpr}:s=1280x720:fps=${FPS},` +
          `drawtext=text='${safeText}':fontcolor=white:fontsize=30:x=20:y=h-th-30:` +
          `box=1:boxcolor=black@0.65:boxborderw=10,` +
          `fade=t=in:st=0:d=0.4,fade=t=out:st=${Math.max(0, dur - 0.4)}:d=0.4[v]`,
        ],
        ["-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-c:a", "aac",
         "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", String(FPS), "-t", String(dur)],
        segOut
      );
      segVids.push(segOut);
      logger.info({ i }, "Segment done");
    }

    const listFile = path.join(dir, "list.txt");
    fs.writeFileSync(listFile, segVids.map(p => `file '${p}'`).join("\n"));

    const out = path.join(dir, "output.mp4");
    await runFFmpeg(
      [listFile],
      ["-f", "concat", "-safe", "0"],
      [],
      ["-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
       "-movflags", "+faststart", "-t", String(TARGET_SEC)],
      out
    );

    const finalDur = getAudioDuration(out);
    logger.info({ id: job.id, finalDur }, "Video DONE");
    job.outputPath = out;
    job.status = "done";

    segVids.forEach(p => { try { fs.unlinkSync(p); } catch {} });
  } catch (err: any) {
    logger.error({ id: job.id, err: err.message }, "processJob error");
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
    throw err;
  }
}

function runFFmpeg(
  inputs: string[], inputOpts: string[],
  filter: string[], outputOpts: string[], output: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    let cmd = ffmpeg();
    for (let i = 0; i < inputs.length; i++) {
      if (i === 0 && inputOpts.length > 0) cmd = cmd.input(inputs[i]!).inputOptions(inputOpts);
      else cmd = cmd.input(inputs[i]!);
    }
    if (filter.length > 0) cmd = cmd.complexFilter(filter);
    cmd.outputOptions(outputOpts).output(output)
      .on("end", () => resolve())
      .on("error", (e: Error) => { logger.error({ err: e.message, output }, "ffmpeg error"); reject(e); })
      .run();
  });
}

async function padAudio(src: string, dst: string, targetDur: number): Promise<void> {
  const actual = getAudioDuration(src);
  if (Math.abs(actual - targetDur) < 0.3) { fs.copyFileSync(src, dst); return; }
  if (actual < targetDur) {
    const pad = targetDur - actual;
    const silFile = dst + ".sil.mp3";
    execSync(`ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${pad}" -c:a libmp3lame "${silFile}" 2>/dev/null`, { timeout: 15000 });
    const lst = dst + ".lst";
    fs.writeFileSync(lst, `file '${src}'\nfile '${silFile}'`);
    await new Promise<void>((res, rej) =>
      ffmpeg().input(lst).inputOptions(["-f", "concat", "-safe", "0"])
        .audioCodec("libmp3lame").output(dst)
        .on("end", () => { try { fs.unlinkSync(lst); fs.unlinkSync(silFile); } catch {} res(); })
        .on("error", (e: Error) => rej(e)).run()
    );
  } else {
    await new Promise<void>((res, rej) =>
      ffmpeg(src).outputOptions(["-t", String(targetDur)]).audioCodec("libmp3lame")
        .output(dst).on("end", () => res()).on("error", (e: Error) => rej(e)).run()
    );
  }
}

async function makeBhaktiImage(out: string, text: string, idx: number): Promise<void> {
  const bgs = ["saddlebrown", "darkorange", "darkgoldenrod", "saddlebrown", "peru"];
  const bg = bgs[idx % bgs.length]!;
  const safe = text.replace(/['"\\:]/g, " ").slice(0, 45);
  try {
    execSync(
      `ffmpeg -y -f lavfi -i "color=c=${bg}:size=1280x720" ` +
      `-vf "drawtext=text='🙏':fontsize=120:x=(w-text_w)/2:y=h/4:fontcolor=gold,` +
      `drawtext=text='${safe}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=2*h/3:` +
      `box=1:boxcolor=black@0.5:boxborderw=12" -frames:v 1 "${out}" 2>/dev/null`,
      { timeout: 15000 }
    );
  } catch {
    execSync(`ffmpeg -y -f lavfi -i "color=c=saddlebrown:size=1280x720" -frames:v 1 "${out}" 2>/dev/null`, { timeout: 10000 });
  }
}

function splitText(text: string): string[] {
  const parts = text.split(/[।\.\!\?]+/).map(s => s.trim()).filter(s => s.length > 4);
  if (parts.length < 2) {
    const words = text.split(/\s+/);
    const n = Math.max(2, Math.ceil(words.length / 10));
    const out: string[] = [];
    for (let i = 0; i < words.length; i += n) out.push(words.slice(i, i + n).join(" "));
    return out.filter(s => s.length > 4);
  }
  const merged: string[] = [];
  let cur = "";
  for (const p of parts) {
    cur = cur ? `${cur}. ${p}` : p;
    if (cur.length > 90) { merged.push(cur.trim()); cur = ""; }
  }
  if (cur.trim().length > 4) merged.push(cur.trim());
  return merged.length > 0 ? merged : [text];
}

export function cleanupJob(id: string): void {
  const job = jobs.get(id);
  if (job?.outputPath) {
    try { fs.rmSync(path.dirname(job.outputPath), { recursive: true, force: true }); } catch {}
  }
  jobs.delete(id);
}
