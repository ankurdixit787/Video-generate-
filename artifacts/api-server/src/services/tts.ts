import { spawnSync, execSync } from "child_process";
import fs from "fs";
import { logger } from "../lib/logger";

const PYTHON_PATHS = [
  "/home/runner/.local/lib/python3.11/site-packages",
  "/home/runner/.local/lib/python3.12/site-packages",
  "/usr/lib/python3/dist-packages",
];

const GTTS_SCRIPT = `
import sys, os
for p in ${JSON.stringify(PYTHON_PATHS)}:
    if p not in sys.path:
        sys.path.insert(0, p)
from gtts import gTTS
text = sys.argv[1]
out  = sys.argv[2]
slow = sys.argv[3] == "slow" if len(sys.argv) > 3 else False
tts  = gTTS(text=text, lang='hi', slow=slow)
tts.save(out)
print(os.path.getsize(out))
`.trim();

const SCRIPT_PATH = "/tmp/_gtts_runner.py";

function ensureScript(): void {
  fs.writeFileSync(SCRIPT_PATH, GTTS_SCRIPT);
}

export function getAudioDuration(p: string): number {
  try {
    const out = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${p}"`,
      { timeout: 10000 }
    ).toString().trim();
    const dur = parseFloat(out);
    return isNaN(dur) || dur <= 0 ? 3 : dur;
  } catch { return 3; }
}

export async function generateTTS(text: string, outputPath: string): Promise<number> {
  ensureScript();

  // Clean text for gTTS — remove special chars but keep Hindi punctuation
  const safe = text
    .replace(/["""''`\\]/g, "")
    .replace(/[^\u0900-\u097F\w\s।,.!?'-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 800); // Allow longer text for better audio

  if (safe.length < 3) {
    logger.warn({ text: text.slice(0, 40) }, "TTS: text too short after cleaning, using silence");
    return makeSilence(outputPath, 5);
  }

  logger.info({ len: safe.length, text: safe.slice(0, 60) }, "TTS: calling gTTS");

  const r = spawnSync("python3", [SCRIPT_PATH, safe, outputPath], {
    timeout: 60000,
    encoding: "utf-8",
  });

  if (r.status === 0 && fs.existsSync(outputPath)) {
    const size = fs.statSync(outputPath).size;
    if (size > 2000) {
      const dur = getAudioDuration(outputPath);
      if (dur >= 1) {
        logger.info({ dur, size, text: safe.slice(0, 40) }, "TTS: gTTS OK");
        return dur;
      }
      logger.warn({ dur, size }, "TTS: gTTS returned tiny duration, retrying with slow=true");
    } else {
      logger.warn({ size }, "TTS: output file too small");
    }
  } else {
    logger.warn({ status: r.status, stderr: (r.stderr || "").slice(0, 300) }, "TTS: gTTS process failed");
  }

  // Retry with slow mode
  logger.info("TTS: retrying with slow=true");
  const r2 = spawnSync("python3", [SCRIPT_PATH, safe, outputPath, "slow"], {
    timeout: 60000, encoding: "utf-8",
  });

  if (r2.status === 0 && fs.existsSync(outputPath)) {
    const size2 = fs.statSync(outputPath).size;
    if (size2 > 2000) {
      const dur2 = getAudioDuration(outputPath);
      if (dur2 >= 1) {
        logger.info({ dur: dur2, size: size2 }, "TTS: gTTS slow=true OK");
        return dur2;
      }
    }
  }

  logger.warn({ stderr: (r2.stderr || "").slice(0, 300) }, "TTS: gTTS retry failed, using silence");
  return makeSilence(outputPath, estimateDuration(safe));
}

function estimateDuration(text: string): number {
  // Hindi speech ~80-100 syllables per minute, ~2 chars per syllable avg
  const words = text.split(/\s+/).length;
  return Math.max(5, Math.round(words * 0.5));
}

function makeSilence(outputPath: string, dur: number): number {
  try {
    execSync(
      `ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${dur}" -c:a libmp3lame -q:a 5 "${outputPath}" 2>/dev/null`,
      { timeout: 15000 }
    );
    logger.info({ dur }, "TTS: silence fallback created");
    return dur;
  } catch {
    return dur;
  }
}
