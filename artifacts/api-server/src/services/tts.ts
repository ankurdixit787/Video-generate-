import { spawnSync, execSync } from "child_process";
import fs from "fs";
import { logger } from "../lib/logger";

const PYTHON_PATHS = [
  "/home/runner/.local/lib/python3.11/site-packages",
  "/usr/lib/python3/dist-packages",
  "/home/runner/.local/lib/python3.12/site-packages",
];

const GTTS_SCRIPT = `
import sys
for p in ${JSON.stringify(PYTHON_PATHS)}:
    if p not in sys.path:
        sys.path.insert(0, p)
from gtts import gTTS
text = sys.argv[1]
out  = sys.argv[2]
tts  = gTTS(text=text, lang='hi', slow=False)
tts.save(out)
import os
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
    return parseFloat(out) || 3;
  } catch { return 3; }
}

export async function generateTTS(text: string, outputPath: string): Promise<number> {
  ensureScript();
  const safe = text.replace(/"/g, "'").replace(/\\/g, "").trim().slice(0, 500);

  logger.info({ text: safe.slice(0, 60) }, "TTS: calling gTTS");

  const r = spawnSync("python3", [SCRIPT_PATH, safe, outputPath], {
    timeout: 40000, encoding: "utf-8",
  });

  if (r.status === 0 && fs.existsSync(outputPath)) {
    const size = fs.statSync(outputPath).size;
    if (size > 1000) {
      const dur = getAudioDuration(outputPath);
      logger.info({ dur, size, text: safe.slice(0, 40) }, "TTS: gTTS OK");
      return dur;
    }
  }
  logger.warn({ stderr: (r.stderr || "").slice(0, 300) }, "TTS: gTTS failed, using silence");

  const words = safe.split(/\s+/).length;
  const silDur = Math.max(4, Math.round(words * 0.45));
  execSync(
    `ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${silDur}" -c:a libmp3lame -q:a 5 "${outputPath}" 2>/dev/null`,
    { timeout: 15000 }
  );
  return silDur;
}
