import TelegramBot from "node-telegram-bot-api";
import fs from "fs";
import os from "os";
import { logger } from "../lib/logger";
import { createVideoJob, getJob, cleanupJob } from "./videoGenerator";
import { getRecentLogs, getErrorLogs, formatLogsForTelegram, clearLogs } from "./logCapture";
import { getNextBhaktiText, getRemainingTopicsCount, resetTopics } from "./textGenerator";

const BOT_TOKEN = process.env["TELEGRAM_BOT_TOKEN"] || "";
const ADMIN_IDS_RAW = process.env["ADMIN_TELEGRAM_IDS"] || "";
const ADMIN_IDS = new Set(
  ADMIN_IDS_RAW.split(",").map((s) => parseInt(s.trim())).filter(Boolean)
);

let bot: TelegramBot | null = null;
let autoScheduler: ReturnType<typeof setInterval> | null = null;
const userSessions = new Map<number, { step: string; text?: string }>();

function isAdmin(chatId: number): boolean {
  if (ADMIN_IDS.size === 0) return true;
  return ADMIN_IDS.has(chatId);
}

function sendChunked(chatId: number, text: string): Promise<void>[] {
  const MAX = 4000;
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += MAX) chunks.push(text.slice(i, i + MAX));
  return chunks.map((chunk) =>
    bot!.sendMessage(chatId, `\`\`\`\n${chunk}\n\`\`\``, { parse_mode: "Markdown" }).then(() => {})
  );
}

export function initBot(): void {
  if (!BOT_TOKEN) {
    logger.warn("TELEGRAM_BOT_TOKEN not set, bot not started");
    return;
  }

  bot = new TelegramBot(BOT_TOKEN, { polling: true });
  logger.info("Telegram bot started with polling");

  bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    userSessions.set(chatId, { step: "idle" });
    const adminMenu = isAdmin(chatId)
      ? `\n\n🔧 *Admin:*\n*/logs* - Server logs\n*/errors* - Sirf errors\n*/status* - Server status\n*/debug* - Full debug\n*/clearlogs* - Logs saaf karo\n*/topics* - Remaining topics`
      : "";
    await bot!.sendMessage(
      chatId,
      `🙏 *Bhakti Video Generator Bot*\n\n` +
      `Main aapke liye Bhakti videos banata hoon:\n` +
      `• Auto bhakti text generate hoga\n` +
      `• Hindi voice over\n` +
      `• Mandir/devo ki images\n` +
      `• Exactly 1 minute ki video\n\n` +
      `🎬 */generate* - Custom text se video\n` +
      `🙏 */bhakti* - Auto bhakti video banao\n` +
      `❓ */help* - Madad` +
      adminMenu,
      { parse_mode: "Markdown" }
    );
  });

  bot.onText(/\/help/, async (msg) => {
    await bot!.sendMessage(
      msg.chat.id,
      `*Kaise use karein:*\n\n` +
      `🙏 */bhakti* - Ek click mein auto bhakti video\n` +
      `📝 */generate* - Apna text deke video banao\n\n` +
      `_Har video exactly 1 minute ki hogi!_\n` +
      `_Bhakti topics kabhi repeat nahi honge!_`,
      { parse_mode: "Markdown" }
    );
  });

  bot.onText(/\/bhakti/, async (msg) => {
    const chatId = msg.chat.id;
    const session = userSessions.get(chatId);
    if (session?.step === "generating") {
      await bot!.sendMessage(chatId, "⏳ Ek video pehle se ban rahi hai. Thoda wait karo.");
      return;
    }

    const text = getNextBhaktiText();
    const remaining = getRemainingTopicsCount();
    userSessions.set(chatId, { step: "generating", text });

    const statusMsg = await bot!.sendMessage(
      chatId,
      `🙏 *Auto Bhakti Video ban rahi hai...*\n\n` +
      `📖 Text: _${text.slice(0, 80)}..._\n\n` +
      `🔤 Text processing\n` +
      `🎙️ Hindi voice generate ho rahi hai\n` +
      `🖼️ Mandir images dhoondh raha hoon\n` +
      `🎬 1 minute video compile ho rahi hai\n\n` +
      `_Remaining topics: ${remaining}_\n` +
      `_Please wait... 2-3 minutes_`,
      { parse_mode: "Markdown" }
    );

    try {
      const jobId = await createVideoJob(text);
      logger.info({ jobId, chatId, type: "bhakti" }, "Bhakti video job created");
      await pollAndSendVideo(chatId, jobId, statusMsg.message_id);
    } catch (err: any) {
      logger.error({ err: err.message }, "Failed to create bhakti video job");
      await bot!.sendMessage(chatId, `❌ Error: ${err.message}\n\nDobara try karo: /bhakti`);
    } finally {
      userSessions.set(chatId, { step: "idle" });
    }
  });

  bot.onText(/\/generate/, async (msg) => {
    const chatId = msg.chat.id;
    userSessions.set(chatId, { step: "waiting_text" });
    await bot!.sendMessage(
      chatId,
      `📝 *Apna text likhein:*\n\nKoi bhi topic!\n\n_Video exactly 1 minute ki hogi._`,
      { parse_mode: "Markdown" }
    );
  });

  bot.onText(/\/topics/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    const remaining = getRemainingTopicsCount();
    await bot!.sendMessage(chatId, `📚 *Topics Status:*\n\nBaaki topics: *${remaining}*\n\n/resettopics - Pool reset karo`, { parse_mode: "Markdown" });
  });

  bot.onText(/\/resettopics/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    resetTopics();
    await bot!.sendMessage(chatId, "✅ Topic pool reset ho gaya! Ab se sab topics phir se available hain.");
  });

  bot.onText(/\/logs(?:\s+(\d+))?/, async (msg, match) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    const count = parseInt(match?.[1] || "30");
    const entries = getRecentLogs(count);
    const text = formatLogsForTelegram(entries);
    await bot!.sendMessage(chatId, `📋 *Last ${count} Logs:*`, { parse_mode: "Markdown" });
    await Promise.all(sendChunked(chatId, text));
  });

  bot.onText(/\/errors/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    const entries = getErrorLogs(20);
    const text = formatLogsForTelegram(entries);
    await bot!.sendMessage(chatId, `❌ *Recent Errors & Warnings:*`, { parse_mode: "Markdown" });
    await Promise.all(sendChunked(chatId, text));
  });

  bot.onText(/\/status/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    const uptime = process.uptime();
    const uptimeStr = `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m ${Math.floor(uptime % 60)}s`;
    const memMB = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
    const freeMem = Math.round(os.freemem() / 1024 / 1024);
    const totalMem = Math.round(os.totalmem() / 1024 / 1024);
    const errorLogs = getErrorLogs(5);
    const recentErrors = errorLogs.length > 0
      ? errorLogs.map((e) => `  ❌ ${e.time}: ${e.msg}`).join("\n")
      : "  ✅ Koi errors nahi";
    const remaining = getRemainingTopicsCount();

    await bot!.sendMessage(
      chatId,
      `🖥️ *Server Status*\n\n` +
      `⏱️ Uptime: \`${uptimeStr}\`\n` +
      `💾 Heap: \`${memMB} MB\`\n` +
      `🧠 RAM: \`${freeMem}/${totalMem} MB free\`\n` +
      `🤖 Bot: \`Running ✅\`\n` +
      `🌐 Node: \`${process.version}\`\n` +
      `📚 Topics remaining: \`${remaining}\`\n\n` +
      `*Recent Errors:*\n${recentErrors}`,
      { parse_mode: "Markdown" }
    );
  });

  bot.onText(/\/debug/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    const allLogs = getRecentLogs(50);
    const text = formatLogsForTelegram(allLogs);
    await bot!.sendMessage(chatId, `🔍 *Full Debug Log (last 50):*`, { parse_mode: "Markdown" });
    await Promise.all(sendChunked(chatId, text));
  });

  bot.onText(/\/clearlogs/, async (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) { await bot!.sendMessage(chatId, "❌ Access denied."); return; }
    clearLogs();
    await bot!.sendMessage(chatId, "✅ Saare logs saaf ho gaye.");
  });

  bot.on("message", async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    if (!text || text.startsWith("/")) return;

    const session = userSessions.get(chatId);
    if (!session || session.step !== "waiting_text") return;

    if (text.trim().length < 10) {
      await bot!.sendMessage(chatId, "❌ Text bahut chhota hai. Thoda zyada likhein.");
      return;
    }

    userSessions.set(chatId, { step: "generating", text });

    const statusMsg = await bot!.sendMessage(
      chatId,
      `⏳ *Video ban rahi hai...*\n\n` +
      `🔤 Text processing\n🎙️ Voice generate ho rahi hai\n🖼️ Images dhoondh raha hoon\n🎬 1 minute video compile ho rahi hai\n\n` +
      `_Please wait... 2-3 minutes_`,
      { parse_mode: "Markdown" }
    );

    try {
      const jobId = await createVideoJob(text.trim());
      logger.info({ jobId, chatId }, "Custom video job created");
      await pollAndSendVideo(chatId, jobId, statusMsg.message_id);
    } catch (err: any) {
      logger.error({ err: err.message }, "Failed to create video job");
      await bot!.sendMessage(chatId, `❌ Error: ${err.message}\n\nDobara try karein: /generate`);
    } finally {
      userSessions.set(chatId, { step: "idle" });
    }
  });

  bot.on("polling_error", (err) => {
    logger.error({ err: (err as Error).message }, "Telegram polling error");
  });
}

async function pollAndSendVideo(chatId: number, jobId: string, statusMsgId: number): Promise<void> {
  const maxWait = 6 * 60 * 1000;
  const pollInterval = 5000;
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await sleep(pollInterval);
    const job = getJob(jobId);

    if (!job) {
      await bot!.sendMessage(chatId, "❌ Job nahi mili. Dobara try karo.");
      return;
    }

    if (job.status === "failed") {
      logger.error({ jobId, error: job.error }, "Job failed");
      await bot!.editMessageText(
        `❌ Video banane mein error:\n\`${job.error}\`\n\nDobara try karo: /bhakti`,
        { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
      ).catch(() => {});
      return;
    }

    if (job.status === "done" && job.outputPath && fs.existsSync(job.outputPath)) {
      try {
        await bot!.editMessageText(
          `✅ *Video ready! Bhej raha hoon...*`,
          { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
        ).catch(() => {});

        const videoStream = fs.createReadStream(job.outputPath);
        await bot!.sendVideo(chatId, videoStream, {
          caption: `🙏 *Bhakti Video*\n\n${job.text.slice(0, 200)}${job.text.length > 200 ? "..." : ""}`,
          parse_mode: "Markdown",
        });

        logger.info({ chatId, jobId }, "Video sent to Telegram");
        cleanupJob(jobId);
      } catch (err: any) {
        logger.error({ err: err.message, jobId }, "Failed to send video");
        await bot!.sendMessage(chatId, `❌ Video bhejna fail hua: ${err.message}`);
      }
      return;
    }

    const elapsed = Math.floor((Date.now() - start) / 1000);
    if (elapsed % 30 === 0 && elapsed > 0) {
      await bot!.editMessageText(
        `⏳ *Video ban rahi hai... (${elapsed}s)*\nPlease wait...`,
        { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
      ).catch(() => {});
    }
  }

  logger.warn({ jobId, chatId }, "Video job timed out");
  await bot!.editMessageText(
    `⏰ Timeout. Dobara try karo: /bhakti`,
    { chat_id: chatId, message_id: statusMsgId }
  ).catch(() => {});
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function stopBot(): void {
  if (autoScheduler) { clearInterval(autoScheduler); autoScheduler = null; }
  if (bot) {
    bot.stopPolling();
    bot = null;
    logger.info("Telegram bot stopped");
  }
}
