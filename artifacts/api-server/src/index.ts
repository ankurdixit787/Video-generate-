import { createServer } from "net";
import app from "./app";
import { logger } from "./lib/logger";
import { initBot, stopBot } from "./services/telegramBot";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error("PORT environment variable is required but was not provided.");
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

function isPortFree(p: number): Promise<boolean> {
  return new Promise((resolve) => {
    const srv = createServer();
    srv.once("error", () => resolve(false));
    srv.once("listening", () => { srv.close(); resolve(true); });
    srv.listen(p);
  });
}

async function startServer(retries = 5): Promise<void> {
  for (let attempt = 0; attempt < retries; attempt++) {
    const free = await isPortFree(port);
    if (free) break;
    logger.warn({ port, attempt }, "Port in use, waiting 2s...");
    await new Promise((r) => setTimeout(r, 2000));
    if (attempt === retries - 1) {
      logger.error({ port }, "Port still in use after retries, exiting");
      process.exit(1);
    }
  }

  app.listen(port, (err) => {
    if (err) {
      logger.error({ err }, "Error listening on port");
      process.exit(1);
    }
    logger.info({ port }, "Server listening");
    initBot();
  });
}

startServer();

process.on("SIGTERM", () => { stopBot(); process.exit(0); });
process.on("SIGINT",  () => { stopBot(); process.exit(0); });
process.on("uncaughtException", (err) => { logger.error({ err: err.message }, "Uncaught exception"); });
process.on("unhandledRejection", (err: any) => { logger.error({ err: err?.message }, "Unhandled rejection"); });
