import https from "https";
import { logger } from "../lib/logger";

const PEXELS_API_KEY = process.env["PEXELS_API_KEY"] || "";

export async function searchImages(query: string, count: number = 5): Promise<string[]> {
  if (PEXELS_API_KEY) {
    return searchPexels(query, count);
  }
  return getUnsplashImages(query, count);
}

async function searchPexels(query: string, count: number): Promise<string[]> {
  return new Promise((resolve) => {
    const encodedQuery = encodeURIComponent(query);
    const options = {
      hostname: "api.pexels.com",
      path: `/v1/search?query=${encodedQuery}&per_page=${count}&orientation=landscape`,
      headers: { Authorization: PEXELS_API_KEY },
    };
    https.get(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          const json = JSON.parse(data);
          const urls = (json.photos || []).map((p: any) => p.src.large2x || p.src.large);
          logger.info({ query, count: urls.length }, "Pexels images found");
          resolve(urls);
        } catch {
          resolve(getUnsplashImages(query, count));
        }
      });
    }).on("error", () => resolve(getUnsplashImages(query, count)));
  });
}

async function getUnsplashImages(query: string, count: number): Promise<string[]> {
  const keywords = query.split(" ").slice(0, 2).join(",");
  const images: string[] = [];
  for (let i = 0; i < count; i++) {
    const seed = Math.floor(Math.random() * 1000) + i;
    images.push(`https://picsum.photos/seed/${seed}/1280/720`);
  }
  logger.info({ query, count }, "Using picsum placeholder images");
  return images;
}

export async function downloadImage(url: string, outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const file = require("fs").createWriteStream(outputPath);
    const getWithRedirect = (reqUrl: string, maxRedirects = 5) => {
      const mod = reqUrl.startsWith("https") ? https : require("http");
      mod.get(reqUrl, {
        headers: { "User-Agent": "Mozilla/5.0" },
      }, (res: any) => {
        if ((res.statusCode === 301 || res.statusCode === 302) && maxRedirects > 0) {
          getWithRedirect(res.headers.location, maxRedirects - 1);
          return;
        }
        res.pipe(file);
        file.on("finish", () => {
          file.close();
          resolve();
        });
      }).on("error", reject);
    };
    getWithRedirect(url);
  });
}
