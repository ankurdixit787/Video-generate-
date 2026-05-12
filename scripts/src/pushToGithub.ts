import https from "https";
import fs from "fs";
import path from "path";

const GITHUB_TOKEN = process.env["GITHUB_TOKEN"];
const OWNER = "ankurdixit787";
const REPO = "Video-generate-";
const BRANCH = "main";

if (!GITHUB_TOKEN) {
  console.error("ERROR: GITHUB_TOKEN not set.");
  process.exit(1);
}

const FILES_TO_PUSH = [
  "artifacts/api-server/src/index.ts",
  "artifacts/api-server/src/app.ts",
  "artifacts/api-server/src/routes/index.ts",
  "artifacts/api-server/src/routes/health.ts",
  "artifacts/api-server/src/routes/video.ts",
  "artifacts/api-server/src/lib/logger.ts",
  "artifacts/api-server/src/services/telegramBot.ts",
  "artifacts/api-server/src/services/videoGenerator.ts",
  "artifacts/api-server/src/services/textGenerator.ts",
  "artifacts/api-server/src/services/imageSearch.ts",
  "artifacts/api-server/src/services/tts.ts",
  "artifacts/api-server/src/services/logCapture.ts",
  "artifacts/api-server/package.json",
  "scripts/src/pushToGithub.ts",
  "scripts/package.json",
];

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");

function githubRequest(method: string, urlPath: string, body?: object): Promise<any> {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : undefined;
    const options = {
      hostname: "api.github.com",
      path: urlPath,
      method,
      headers: {
        Authorization: `token ${GITHUB_TOKEN}`,
        "User-Agent": "replit-push-script",
        "Content-Type": "application/json",
        Accept: "application/vnd.github.v3+json",
        ...(data ? { "Content-Length": Buffer.byteLength(data) } : {}),
      },
    };

    const req = https.request(options, (res) => {
      let raw = "";
      res.on("data", (chunk) => (raw += chunk));
      res.on("end", () => {
        try { resolve(JSON.parse(raw)); } catch { resolve(raw); }
      });
    });
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}

async function getFileSha(filePath: string): Promise<string | undefined> {
  const res = await githubRequest("GET", `/repos/${OWNER}/${REPO}/contents/${filePath}?ref=${BRANCH}`);
  return res?.sha;
}

async function pushFile(relPath: string): Promise<void> {
  const absPath = path.join(ROOT, relPath);
  if (!fs.existsSync(absPath)) {
    console.log(`⏭  Skipping (not found): ${relPath}`);
    return;
  }

  const content = fs.readFileSync(absPath);
  const encoded = content.toString("base64");
  const sha = await getFileSha(relPath);

  const body: any = {
    message: `Update ${relPath} - bhakti video bot`,
    content: encoded,
    branch: BRANCH,
  };
  if (sha) body.sha = sha;

  const res = await githubRequest("PUT", `/repos/${OWNER}/${REPO}/contents/${relPath}`, body);

  if (res?.content?.name) {
    console.log(`✅ Pushed: ${relPath}`);
  } else if (res?.message) {
    console.error(`❌ Failed ${relPath}: ${res.message}`);
  }
}

async function main() {
  console.log(`\n🚀 Pushing ${FILES_TO_PUSH.length} files to GitHub...\n`);
  for (const file of FILES_TO_PUSH) {
    await pushFile(file);
  }
  console.log("\n✅ Done! Check: https://github.com/ankurdixit787/Video-generate-");
}

main().catch((err) => {
  console.error("Fatal:", err.message);
  process.exit(1);
});
