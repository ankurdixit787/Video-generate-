import TelegramBot from "node-telegram-bot-api";
import fs from "fs";
import os from "os";
import { logger } from "../lib/logger";
import { createVideoJob, getJob, cleanupJob } from "./videoGenerator";
import { getRecentLogs, getErrorLogs, formatLogsForTelegram, clearLogs } from "./logCapture";
import { getNextBhaktiText, getRemainingTopicsCount, resetTopics } from "./textGenerator";

const BOT_TOKEN = process.env["TELEGRAM_BOT_TOKEN"] || "";

let bot: TelegramBot | null = null;
const userSessions = new Map<number, { step: string; text?: string }>();

function reply(chatId: number, text: string, opts?: TelegramBot.SendMessageOptions): Promise<TelegramBot.Message> {
  return bot!.sendMessage(chatId, text, { parse_mode: "Markdown", ...opts });
}

function sendChunked(chatId: number, text: string): Array<Promise<void>> {
  const MAX = 3800;
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += MAX) chunks.push(text.slice(i, i + MAX));
  return chunks.map((c) => reply(chatId, `\`\`\`\n${c}\n\`\`\``).then(() => {}));
}

const MAIN_MENU = `🙏 *Bhakti Video Bot - Menu*

🎬 /bhakti — Auto bhakti video banao \\(1 min\\)
📝 /generate — Apna text deke video banao
ℹ️ /help — Madad

🔧 *Admin:*
📋 /logs — Server logs
❌ /errors — Sirf errors
🖥️ /status — Server health
🔍 /debug — Full debug
🗑️ /clearlogs — Logs clear karo
📚 /topics — Remaining topics`;

const MAIN_MENU_PLAIN = `🙏 *Bhakti Video Bot - Menu*\n\n🎬 /bhakti - Auto bhakti video (1 min)\n📝 /generate - Apna text deke video\nℹ️ /help - Madad\n\n🔧 *Admin:*\n📋 /logs - Server logs\n❌ /errors - Errors\n🖥️ /status - Server health`;

export function initBot(): void {
  if (!BOT_TOKEN) {
    logger.warn("TELEGRAM_BOT_TOKEN not set, bot not started");
    return;
  }

  bot = new TelegramBot(BOT_TOKEN, { polling: true });
  logger.info("Telegram bot started");

  bot.on("message", async (msg) => {
    const chatId = msg.chat.id;
    const text = (msg.text || "").trim();

    if (!text) return;

    logger.info({ chatId, text: text.slice(0, 60) }, "Bot message received");

    try {
      await handleMessage(chatId, text, msg);
    } catch (err: any) {
      logger.error({ err: err.message, chatId }, "Bot message handler error");
      try {
        await reply(chatId, `❌ Error: ${err.message}`);
      } catch {}
    }
  });

  bot.on("polling_error", (err) => {
    logger.error({ err: (err as Error).message }, "Telegram polling error");
  });

  bot.on("error", (err) => {
    logger.error({ err: (err as Error).message }, "Telegram bot error");
  });

  logger.info("Telegram bot handlers registered");
}

async function handleMessage(chatId: number, text: string, msg: TelegramBot.Message): Promise<void> {
  const session = userSessions.get(chatId) ?? { step: "idle" };

  // ── COMMANDS ──────────────────────────────────────────────────
  if (text.startsWith("/")) {
    const cmd = text.split(" ")[0]!.split("@")[0]!.toLowerCase();

    switch (cmd) {
      case "/start":
        userSessions.set(chatId, { step: "idle" });
        await reply(chatId, `Namaste! 🙏\n\n${MAIN_MENU_PLAIN}\n\n_Seedha /bhakti likh ke shuru karo!_`);
        return;

      case "/help":
        await reply(chatId,
          `*Madad:*\n\n` +
          `🙏 */bhakti* — Ek click mein auto bhakti video (1 min)\n` +
          `📝 */generate* — Apna text deke video banao\n\n` +
          `*Admin Commands:*\n` +
          `📋 */logs* — Last 30 server logs\n` +
          `❌ */errors* — Sirf errors/warnings\n` +
          `🖥️ */status* — Server health\n` +
          `🔍 */debug* — Full debug log\n` +
          `🗑️ */clearlogs* — Logs saaf karo\n` +
          `📚 */topics* — Kitne topics baaki hain\n\n` +
          `_Sabhi commands private chat mein kaam karte hain._`
        );
        return;

      case "/bhakti":
        await handleBhakti(chatId, session);
        return;

      case "/generate":
        userSessions.set(chatId, { step: "waiting_text" });
        await reply(chatId, `📝 *Apna text likhein:*\n\nKoi bhi topic - bhakti, motivational, news!\n\n_Video exactly 1 minute ki hogi._`);
        return;

      case "/logs": {
        const parts = text.split(" ");
        const count = parseInt(parts[1] ?? "30") || 30;
        const entries = getRecentLogs(count);
        const logText = formatLogsForTelegram(entries);
        await reply(chatId, `📋 *Last ${count} Logs:*`);
        await Promise.all(sendChunked(chatId, logText));
        return;
      }

      case "/errors": {
        const entries = getErrorLogs(20);
        const logText = formatLogsForTelegram(entries);
        await reply(chatId, `❌ *Recent Errors & Warnings:*`);
        await Promise.all(sendChunked(chatId, logText));
        return;
      }

      case "/status": {
        const uptime = process.uptime();
        const uh = Math.floor(uptime / 3600);
        const um = Math.floor((uptime % 3600) / 60);
        const us = Math.floor(uptime % 60);
        const mem = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
        const free = Math.round(os.freemem() / 1024 / 1024);
        const total = Math.round(os.totalmem() / 1024 / 1024);
        const errs = getErrorLogs(3);
        const errStr = errs.length > 0
          ? errs.map((e) => `❌ ${e.time}: ${e.msg.slice(0, 60)}`).join("\n")
          : "✅ Koi errors nahi";
        await reply(chatId,
          `🖥️ *Server Status*\n\n` +
          `⏱️ Uptime: \`${uh}h ${um}m ${us}s\`\n` +
          `💾 Heap: \`${mem} MB\`\n` +
          `🧠 RAM: \`${free}/${total} MB free\`\n` +
          `🤖 Bot: \`Running ✅\`\n` +
          `🌐 Node: \`${process.version}\`\n` +
          `📚 Topics left: \`${getRemainingTopicsCount()}\`\n\n` +
          `*Last 3 Errors:*\n${errStr}`
        );
        return;
      }

      case "/debug": {
        const entries = getRecentLogs(50);
        const logText = formatLogsForTelegram(entries);
        await reply(chatId, `🔍 *Full Debug Log (last 50):*`);
        await Promise.all(sendChunked(chatId, logText));
        return;
      }

      case "/clearlogs":
        clearLogs();
        await reply(chatId, "✅ Saare logs saaf ho gaye.");
        return;

      case "/topics": {
        const remaining = getRemainingTopicsCount();
        await reply(chatId,
          `📚 *Topics Pool:*\n\nBaaki topics: *${remaining}/30*\n\n` +
          `_Saare khatam hone par automatically reset ho jaate hain._\n\n` +
          `*/resettopics* - Abhi reset karo`
        );
        return;
      }

      case "/resettopics":
        resetTopics();
        await reply(chatId, "✅ Topic pool reset ho gaya! Sab 30 topics dobara available hain.");
        return;

      default:
        await reply(chatId,
          `❓ Yeh command samajh nahi aaya: \`${cmd}\`\n\n${MAIN_MENU_PLAIN}`
        );
        return;
    }
  }

  // ── PLAIN TEXT ────────────────────────────────────────────────
  if (session.step === "waiting_text") {
    if (text.length < 10) {
      await reply(chatId, "❌ Text bahut chhota hai (min 10 characters). Thoda zyada likhein.");
      return;
    }
    await handleGenerateVideo(chatId, text);
    return;
  }

  // Any other text → show menu with smart response
  const lower = text.toLowerCase();
  if (lower.includes("hello") || lower.includes("hi") || lower.includes("namaste") || lower.includes("helo")) {
    await reply(chatId,
      `Namaste! 🙏 Swagat hai!\n\n${MAIN_MENU_PLAIN}\n\n_/bhakti likh ke seedha video banao!_`
    );
  } else if (lower.includes("video") || lower.includes("bana") || lower.includes("create")) {
    await reply(chatId, `🎬 Video banane ke liye:\n\n/bhakti - Auto bhakti video\n/generate - Apna text deke video`);
  } else if (lower.includes("help") || lower.includes("kaise") || lower.includes("how")) {
    await reply(chatId,
      `*Kaise use karein:*\n\n` +
      `1️⃣ /bhakti likhein → auto video aayegi\n` +
      `2️⃣ /generate likhein → apna text daalein → video aayegi\n\n` +
      `_Har video exactly 1 minute ki hogi!_`
    );
  } else {
    await reply(chatId,
      `🙏 Samjha nahi. Yeh commands use karein:\n\n` +
      `/bhakti - Auto bhakti video banao\n` +
      `/generate - Custom text se video\n` +
      `/help - Madad`
    );
  }
}

async function handleBhakti(chatId: number, session: { step: string }): Promise<void> {
  if (session.step === "generating") {
    await reply(chatId, "⏳ Ek video pehle se ban rahi hai. Thoda wait karo phir /bhakti karo.");
    return;
  }

  const text = getNextBhaktiText();
  const remaining = getRemainingTopicsCount();
  userSessions.set(chatId, { step: "generating" });

  const statusMsg = await reply(chatId,
    `🙏 *Bhakti Video ban rahi hai...*\n\n` +
    `📖 _${text.slice(0, 90)}..._\n\n` +
    `🎙️ Hindi voice generate ho rahi hai\n` +
    `🖼️ Bhakti images download ho rahi hain\n` +
    `🎬 1 minute video compile ho rahi hai\n\n` +
    `📚 Topics baaki: ${remaining}\n` +
    `_Please wait... 2-3 minutes_`
  );

  try {
    const jobId = await createVideoJob(text);
    logger.info({ jobId, chatId, type: "bhakti" }, "Bhakti video job created");
    await pollAndSendVideo(chatId, jobId, statusMsg.message_id);
  } catch (err: any) {
    logger.error({ err: err.message }, "Bhakti video job failed");
    await reply(chatId, `❌ Error: ${err.message}\n\nDobara try karo: /bhakti`);
  } finally {
    userSessions.set(chatId, { step: "idle" });
  }
}

async function handleGenerateVideo(chatId: number, text: string): Promise<void> {
  userSessions.set(chatId, { step: "generating" });

  const statusMsg = await reply(chatId,
    `⏳ *Video ban rahi hai...*\n\n` +
    `🎙️ Voice generate ho rahi hai\n` +
    `🖼️ Images dhoondh raha hoon\n` +
    `🎬 1 minute video compile ho rahi hai\n\n` +
    `_Please wait... 2-3 minutes_`
  );

  try {
    const jobId = await createVideoJob(text);
    logger.info({ jobId, chatId }, "Custom video job created");
    await pollAndSendVideo(chatId, jobId, statusMsg.message_id);
  } catch (err: any) {
    logger.error({ err: err.message }, "Custom video job failed");
    await reply(chatId, `❌ Error: ${err.message}\n\nDobara try karo: /generate`);
  } finally {
    userSessions.set(chatId, { step: "idle" });
  }
}

async function pollAndSendVideo(chatId: number, jobId: string, statusMsgId: number): Promise<void> {
  const maxWait = 6 * 60 * 1000;
  const interval = 5000;
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await sleep(interval);
    const job = getJob(jobId);

    if (!job) {
      await reply(chatId, "❌ Job nahi mili. Dobara try karo: /bhakti");
      return;
    }

    if (job.status === "failed") {
      logger.error({ jobId, error: job.error }, "Job failed");
      await bot!.editMessageText(
        `❌ *Error:*\n\`${job.error?.slice(0, 200)}\`\n\n/errors se detail dekho\nDobara: /bhakti`,
        { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
      ).catch(() => reply(chatId, `❌ Video failed: ${job.error?.slice(0, 200)}`));
      return;
    }

    if (job.status === "done" && job.outputPath && fs.existsSync(job.outputPath)) {
      try {
        await bot!.editMessageText(
          `✅ *Video ready! Bhej raha hoon...*`,
          { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
        ).catch(() => {});

        await bot!.sendVideo(chatId, fs.createReadStream(job.outputPath), {
          caption: `🙏 *Bhakti Video*\n\n${job.text.slice(0, 200)}${job.text.length > 200 ? "..." : ""}`,
          parse_mode: "Markdown",
        });

        logger.info({ chatId, jobId }, "Video sent to Telegram successfully");
        cleanupJob(jobId);
      } catch (err: any) {
        logger.error({ err: err.message, jobId }, "Failed to send video");
        await reply(chatId, `❌ Video bhejna fail hua: ${err.message}\n\n/errors se details dekho`);
      }
      return;
    }

    const elapsed = Math.floor((Date.now() - start) / 1000);
    if (elapsed % 30 === 0 && elapsed > 0) {
      await bot!.editMessageText(
        `⏳ *Ban rahi hai... ${elapsed}s*\nPlease wait karo...`,
        { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
      ).catch(() => {});
    }
  }

  logger.warn({ jobId, chatId }, "Video job timed out");
  await bot!.editMessageText(
    `⏰ Timeout. Dobara: /bhakti`,
    { chat_id: chatId, message_id: statusMsgId }
  ).catch(() => {});
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function stopBot(): void {
  if (bot) { bot.stopPolling(); bot = null; logger.info("Telegram bot stopped"); }
}
