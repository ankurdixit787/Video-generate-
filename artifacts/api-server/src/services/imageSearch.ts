import https from "https";
import http from "http";
import fs from "fs";
import { logger } from "../lib/logger";

const BHAKTI_KEYWORDS: Record<string, string[]> = {
  ram:      ["ram+temple+india", "ayodhya+temple+india", "ramayana+india"],
  krishna:  ["krishna+temple+vrindavan", "mathura+india+temple", "radha+krishna"],
  hanuman:  ["hanuman+temple+india", "bajrangbali+india", "monkey+god+india"],
  shiv:     ["shiva+temple+india", "mahadev+temple", "shivlinga+temple"],
  durga:    ["durga+temple+india", "navratri+goddess+india", "mata+temple+india"],
  ganesh:   ["ganesh+temple+india", "ganesha+idol", "ganpati+india"],
  lakshmi:  ["lakshmi+temple+india", "goddess+wealth+india", "diwali+temple"],
  sai:      ["shirdi+sai+temple", "sai+baba+india", "sai+temple"],
  kali:     ["kali+temple+india", "goddess+india+dark", "shakti+temple"],
  tirupati: ["tirupati+temple+india", "balaji+tirumala", "andhra+temple"],
  vaishno:  ["vaishno+devi+jammu", "mountain+temple+india", "mata+devi+temple"],
  kashi:    ["varanasi+ganga+india", "kashi+temple", "banaras+ghat+india"],
};

const FALLBACK_KEYWORDS = ["temple+india+hindu", "hinduism+india+worship", "india+temple+god", "bhakti+india+temple"];

function pickKeyword(text: string): string {
  const lower = text.toLowerCase();
  for (const [key, vals] of Object.entries(BHAKTI_KEYWORDS)) {
    if (lower.includes(key)) {
      return vals[Math.floor(Math.random() * vals.length)]!;
    }
  }
  return FALLBACK_KEYWORDS[Math.floor(Math.random() * FALLBACK_KEYWORDS.length)]!;
}

export async function searchImages(query: string, _count = 1): Promise<string[]> {
  const kw = pickKeyword(query);
  const url = `https://loremflickr.com/1280/720/${kw}`;
  logger.info({ kw, query: query.slice(0, 40) }, "Image keyword selected");
  return [url];
}

export async function downloadImage(url: string, outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const follow = (u: string, hops = 0): void => {
      if (hops > 8) { reject(new Error("Too many redirects")); return; }
      let mod: typeof https | typeof http;
      try {
        const parsed = new URL(u);
        mod = parsed.protocol === "https:" ? https : http;
      } catch {
        reject(new Error(`Invalid URL: ${u}`)); return;
      }
      const req = mod.get(u, {
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; BhaktiVideoBot/1.0)",
          "Accept": "image/jpeg,image/png,image/*",
        },
      }, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 303) {
          const loc = res.headers.location;
          if (!loc) { reject(new Error("Redirect with no Location")); return; }
          const nextUrl = loc.startsWith("http") ? loc : new URL(loc, u).href;
          res.resume();
          follow(nextUrl, hops + 1);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} for ${u}`)); return;
        }
        const file = fs.createWriteStream(outputPath);
        res.pipe(file);
        file.on("finish", () => { file.close(); resolve(); });
        file.on("error", reject);
      });
      req.on("error", reject);
      req.setTimeout(20000, () => { req.destroy(); reject(new Error("Image download timeout")); });
    };
    follow(url);
  });
}
