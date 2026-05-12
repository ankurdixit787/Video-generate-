import { execSync, spawnSync } from "child_process";
import fs from "fs";
import { logger } from "../lib/logger";

export async function generateTTS(text: string, outputPath: string): Promise<number> {
  const wavPath = outputPath.replace(/\.mp3$/, ".wav");
  const safeText = text.replace(/"/g, "'").replace(/`/g, "'").replace(/\\/g, "");

  const espeakBin = "/nix/store/02sy4i533rf5zcqal2yblk6mcyfpdsh8-espeak-ng-1.51.1/bin/espeak-ng";

  const gttsScript = `
import sys
from gtts import gTTS
text = sys.argv[1]
lang = 'hi'
tts = gTTS(text=text, lang=lang, slow=False)
tts.save(sys.argv[2])
`.trim();

  const scriptPath = "/tmp/gtts_run.py";
  fs.writeFileSync(scriptPath, gttsScript);

  const result = spawnSync("python3", [scriptPath, safeText, outputPath], {
    timeout: 30000,
    encoding: "utf-8",
  });

  if (result.status === 0 && fs.existsSync(outputPath) && fs.statSync(outputPath).size > 500) {
    const dur = getAudioDuration(outputPath);
    logger.info({ dur, text: text.slice(0, 40) }, "gTTS audio generated");
    return dur;
  }

  logger.warn({ stderr: result.stderr?.slice(0, 200) }, "gTTS failed, trying espeak-ng");

  if (fs.existsSync(espeakBin)) {
    spawnSync(espeakBin, ["-v", "hi", "-s", "140", "-w", wavPath, safeText], { timeout: 20000 });
    if (fs.existsSync(wavPath) && fs.statSync(wavPath).size > 100) {
      execSync(`ffmpeg -y -i "${wavPath}" -codec:a libmp3lame -qscale:a 2 "${outputPath}" 2>/dev/null`);
      try { fs.unlinkSync(wavPath); } catch {}
      const dur = getAudioDuration(outputPath);
      logger.info({ dur }, "espeak-ng audio generated");
      return dur;
    }
  }

  logger.warn("All TTS failed, generating silence");
  const words = safeText.split(/\s+/).length;
  const silenceDur = Math.max(3, Math.round(words * 0.4));
  execSync(`ffmpeg -y -f lavfi -i "aevalsrc=0:s=44100:d=${silenceDur}" -c:a libmp3lame "${outputPath}" 2>/dev/null`);
  return silenceDur;
}

export function getAudioDuration(audioPath: string): number {
  try {
    const out = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${audioPath}"`,
      { timeout: 10000 }
    ).toString().trim();
    return parseFloat(out) || 3;
  } catch {
    return 3;
  }
}
