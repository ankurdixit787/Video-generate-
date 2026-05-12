import https from "https";
import http from "http";
import fs from "fs";
import { logger } from "../lib/logger";

const BHAKTI_KEYWORDS: Record<string, string[]> = {
  ram:      ["ram,temple,ayodhya", "ramayana,india,temple", "hindu,temple,india"],
  krishna:  ["krishna,temple,mathura", "vrindavan,krishna,india", "radha,krishna,temple"],
  hanuman:  ["hanuman,temple,india", "bajrangbali,hinduism", "temple,monkey,india"],
  shiv:     ["shiva,temple,india", "mahadev,lingam,temple", "shivlinga,india,temple"],
  durga:    ["durga,temple,india", "navratri,goddess,india", "mata,temple,india"],
  ganesh:   ["ganesh,temple,india", "ganesha,idol,temple", "ganpati,india"],
  lakshmi:  ["lakshmi,temple,india", "goddess,wealth,india", "diwali,india,temple"],
  sai:      ["shirdi,sai,temple", "sai,baba,india", "sai,temple,india"],
  kali:     ["kali,temple,india", "goddess,india,temple", "shakti,temple,india"],
  tirupati: ["tirupati,temple,india", "balaji,temple,tirumala", "andhra,temple,india"],
  vaishno:  ["vaishno,devi,temple", "jammu,temple,india", "mountain,temple,india"],
  kashi:    ["varanasi,ganga,india", "kashi,vishwanath,temple", "banaras,india,ghat"],
  default:  ["temple,india,hindu", "hinduism,india,worship", "india,temple,god", "bhakti,india,devotional"],
};

function pickKeyword(text: string): string {
  const lower = text.toLowerCase();
  for (const [key, vals] of Object.entries(BHAKTI_KEYWORDS)) {
    if (key !== "default" && lower.includes(key)) {
      return vals[Math.floor(Math.random() * vals.length)]!;
    }
  }
  const def = BHAKTI_KEYWORDS["default"]!;
  return def[Math.floor(Math.random() * def.length)]!;
}

export async function searchImages(query: string, _count = 1): Promise<string[]> {
  const kw = pickKeyword(query);
  const url = `https://loremflickr.com/1280/720/${encodeURIComponent(kw)}`;
  logger.info({ kw, query: query.slice(0, 40) }, "Image search keyword");
  return [url];
}

export async function downloadImage(url: string, outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const follow = (u: string, hops = 0) => {
      if (hops > 6) { reject(new Error("Too many redirects")); return; }
      const mod = u.startsWith("https") ? https : http;
      mod.get(u, {
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; BhaktiBot/1.0)",
          "Accept": "image/jpeg,image/*",
        },
      }, (res) => {
        if ((res.statusCode === 301 || res.statusCode === 302) && res.headers.location) {
          follow(res.headers.location, hops + 1);
          return;
        }
        if (res.statusCode !== 200) { reject(new Error(`HTTP ${res.statusCode}`)); return; }
        const file = fs.createWriteStream(outputPath);
        res.pipe(file);
        file.on("finish", () => { file.close(); resolve(); });
        file.on("error", reject);
      }).on("error", reject);
    };
    follow(url);
  });
}
