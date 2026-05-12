import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import https from "https";
import http from "http";
import { logger } from "../lib/logger";

export async function generateTTS(text: string, outputPath: string): Promise<void> {
  const encodedText = encodeURIComponent(text);
  const lang = "hi";
  const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${encodedText}&tl=${lang}&client=tw-ob`;

  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    const request = https.get(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://translate.google.com/",
      },
    }, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        const redirectUrl = response.headers.location!;
        https.get(redirectUrl, (res) => {
          res.pipe(file);
          file.on("finish", () => {
            file.close();
            logger.info({ outputPath }, "TTS audio generated");
            resolve();
          });
        }).on("error", reject);
        return;
      }
      response.pipe(file);
      file.on("finish", () => {
        file.close();
        logger.info({ outputPath }, "TTS audio generated");
        resolve();
      });
    });
    request.on("error", (err) => {
      fs.unlink(outputPath, () => {});
      reject(err);
    });
  });
}

export async function generateTTSFallback(text: string, outputPath: string): Promise<void> {
  try {
    const safeText = text.replace(/'/g, "\\'").replace(/"/g, '\\"');
    execSync(`espeak -v hi -s 150 -w "${outputPath}.wav" "${safeText}" 2>/dev/null || espeak -s 150 -w "${outputPath}.wav" "${safeText}"`, { timeout: 30000 });
    execSync(`ffmpeg -y -i "${outputPath}.wav" "${outputPath}" 2>/dev/null`);
    fs.unlinkSync(`${outputPath}.wav`);
    logger.info({ outputPath }, "TTS fallback generated with espeak");
  } catch {
    execSync(`ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" "${outputPath}" 2>/dev/null`);
    logger.warn({ outputPath }, "Using silent audio fallback");
  }
}
