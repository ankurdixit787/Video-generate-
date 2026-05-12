import { execSync } from "child_process";
import app from "./app";
import { logger } from "./lib/logger";
import { initBot, stopBot } from "./services/telegramBot";

const rawPort = process.env["PORT"];
if (!rawPort) throw new Error("PORT env var required");
const port = Number(rawPort);
if (Number.isNaN(port) || port <= 0) throw new Error(`Invalid PORT: "${rawPort}"`);

try {
  execSync(`fuser -k ${port}/tcp 2>/dev/null || true`, { timeout: 5000 });
} catch {}

app.listen(port, (err) => {
  if (err) { logger.error({ err }, "Listen failed"); process.exit(1); }
  logger.info({ port }, "Server listening");
  initBot();
});

process.on("SIGTERM", () => { stopBot(); process.exit(0); });
process.on("SIGINT",  () => { stopBot(); process.exit(0); });
process.on("uncaughtException",  (err) => logger.error({ err: err.message }, "uncaughtException"));
process.on("unhandledRejection", (err: any) => logger.error({ err: err?.message }, "unhandledRejection"));
