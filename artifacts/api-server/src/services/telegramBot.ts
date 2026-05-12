import TelegramBot from "node-telegram-bot-api";
import fs from "fs";
import os from "os";
import { logger } from "../lib/logger";
import { createVideoJob, getJob, cleanupJob } from "./videoGenerator";
import { getRecentLogs, getErrorLogs, formatLogsForTelegram, clearLogs } from "./logCapture";
import { getNextBhaktiText, getRemainingTopicsCount, resetTopics } from "./textGenerator";
import { chatWithAI, generateBhaktiText, clearConversation } from "./aiService";

const BOT_TOKEN = process.env["TELEGRAM_BOT_TOKEN"] || "";
const AI_ENABLED = !!(process.env["AI_INTEGRATIONS_GEMINI_BASE_URL"] && process.env["AI_INTEGRATIONS_GEMINI_API_KEY"]);

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

const HELP_TEXT =
  `🙏 *Bhakti Video Bot*\n\n` +
  `🎬 /bhakti — Auto bhakti video (1 min)\n` +
  `✨ /aibhakti — AI se naya bhakti text generate karke video\n` +
  `📝 /generate — Apna text deke video banao\n` +
  `💬 /chat — AI se baat karo (development help, koi bhi sawaal)\n` +
  `🗑️ /newchat — AI conversation reset karo\n` +
  `ℹ️ /help — Yeh menu\n\n` +
  `🔧 *Admin:*\n` +
  `📋 /logs — Server logs\n` +
  `❌ /errors — Sirf errors\n` +
  `🖥️ /status — Server health\n` +
  `🔍 /debug — Full debug\n` +
  `🗑️ /clearlogs — Logs clear\n` +
  `📚 /topics — Topics remaining`;

export function initBot(): void {
  if (!BOT_TOKEN) { logger.warn("TELEGRAM_BOT_TOKEN not set, bot not started"); return; }

  bot = new TelegramBot(BOT_TOKEN, { polling: true });
  logger.info({ aiEnabled: AI_ENABLED }, "Telegram bot started");

  bot.on("message", async (msg) => {
    const chatId = msg.chat.id;
    const text = (msg.text || "").trim();
    if (!text) return;

    logger.info({ chatId, text: text.slice(0, 80) }, "Bot message received");

    try {
      await handleMessage(chatId, text);
    } catch (err: any) {
      logger.error({ err: err.message, chatId }, "Bot handler error");
      try { await reply(chatId, `❌ Error: ${err.message}`); } catch {}
    }
  });

  bot.on("polling_error", (err) => logger.error({ err: (err as Error).message }, "Polling error"));
  bot.on("error", (err) => logger.error({ err: (err as Error).message }, "Bot error"));

  logger.info("Telegram bot handlers registered");
}

async function handleMessage(chatId: number, text: string): Promise<void> {
  const session = userSessions.get(chatId) ?? { step: "idle" };

  // ── COMMANDS ──────────────────────────────────────────────────
  if (text.startsWith("/")) {
    const cmd = text.split(" ")[0]!.split("@")[0]!.toLowerCase();
    const args = text.slice(cmd.length).trim();

    switch (cmd) {
      case "/start":
        userSessions.set(chatId, { step: "idle" });
        await reply(chatId,
          `Namaste! 🙏\n\n${HELP_TEXT}\n\n` +
          `_Seedha /bhakti likhke shuru karo, ya /chat se koi bhi sawaal pucho!_`
        );
        return;

      case "/help":
        await reply(chatId, HELP_TEXT);
        return;

      case "/chat":
        if (args.length > 2) {
          await handleAIChat(chatId, args);
        } else {
          userSessions.set(chatId, { step: "chat_mode" });
          await reply(chatId,
            `💬 *AI Chat Mode*\n\n` +
            `Ab seedha message likhein — main har cheez mein madad karunga:\n` +
            `• 🐛 Error fix karo\n` +
            `• 💻 Code likhna\n` +
            `• ❓ Koi bhi sawaal\n` +
            `• 🙏 Bhakti ya general baat\n\n` +
            `_/bhakti ya /generate se video bana sakte ho kabhi bhi_\n` +
            `_/newchat se conversation reset karo_`
          );
        }
        return;

      case "/newchat":
        clearConversation(chatId);
        userSessions.set(chatId, { step: "chat_mode" });
        await reply(chatId, "✅ Naya conversation shuru! Ab kuch bhi pucho.");
        return;

      case "/bhakti":
        await handleBhakti(chatId, session, false);
        return;

      case "/aibhakti":
        await handleBhakti(chatId, session, true);
        return;

      case "/generate":
        userSessions.set(chatId, { step: "waiting_text" });
        await reply(chatId,
          `📝 *Apna text likhein:*\n\nKoi bhi topic likho — bhakti, motivational, news!\n\n_Video exactly 1 minute ki hogi._`
        );
        return;

      case "/logs": {
        const count = parseInt(args) || 30;
        const entries = getRecentLogs(count);
        await reply(chatId, `📋 *Last ${count} Logs:*`);
        await Promise.all(sendChunked(chatId, formatLogsForTelegram(entries)));
        return;
      }

      case "/errors": {
        const entries = getErrorLogs(20);
        await reply(chatId, `❌ *Recent Errors & Warnings:*`);
        await Promise.all(sendChunked(chatId, formatLogsForTelegram(entries)));
        return;
      }

      case "/status": {
        const up = process.uptime();
        const mem = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
        const errCount = getErrorLogs(5).length;
        await reply(chatId,
          `🖥️ *Server Status*\n\n` +
          `⏱️ Uptime: \`${Math.floor(up / 3600)}h ${Math.floor((up % 3600) / 60)}m\`\n` +
          `💾 Heap: \`${mem} MB\`\n` +
          `🧠 RAM Free: \`${Math.round(os.freemem() / 1024 / 1024)} MB\`\n` +
          `🤖 Bot: \`Running ✅\`\n` +
          `🧠 AI: \`${AI_ENABLED ? "Gemini ✅" : "Disabled ❌"}\`\n` +
          `🌐 Node: \`${process.version}\`\n` +
          `📚 Topics left: \`${getRemainingTopicsCount()}/30\`\n` +
          `⚠️ Recent errors: \`${errCount}\``
        );
        return;
      }

      case "/debug": {
        const entries = getRecentLogs(50);
        await reply(chatId, `🔍 *Full Debug (last 50):*`);
        await Promise.all(sendChunked(chatId, formatLogsForTelegram(entries)));
        return;
      }

      case "/clearlogs":
        clearLogs();
        await reply(chatId, "✅ Logs saaf ho gaye.");
        return;

      case "/topics": {
        const rem = getRemainingTopicsCount();
        await reply(chatId,
          `📚 *Topics Pool:*\n\nBaaki: *${rem}/30*\n\n/resettopics — Abhi reset karo`
        );
        return;
      }

      case "/resettopics":
        resetTopics();
        await reply(chatId, "✅ Topic pool reset! Sab 30 topics dobara available hain.");
        return;

      default:
        await reply(chatId, `❓ Yeh command pata nahi: \`${cmd}\`\n\n${HELP_TEXT}`);
        return;
    }
  }

  // ── PLAIN TEXT ────────────────────────────────────────────────

  // Waiting for custom video text
  if (session.step === "waiting_text") {
    if (text.length < 10) {
      await reply(chatId, "❌ Text bahut chhota hai (min 10 characters). Thoda zyada likho.");
      return;
    }
    await handleGenerateVideo(chatId, text);
    return;
  }

  // Chat mode or any message → AI response
  if (AI_ENABLED) {
    userSessions.set(chatId, { ...session, step: "chat_mode" });
    await handleAIChat(chatId, text);
  } else {
    // Fallback without AI
    const lower = text.toLowerCase();
    if (lower.includes("hello") || lower.includes("hi") || lower.includes("namaste")) {
      await reply(chatId, `Namaste! 🙏\n\n${HELP_TEXT}`);
    } else {
      await reply(chatId, `🙏 /bhakti — Video banao\n💬 /help — Saari commands\n\n_Agar AI chat chahiye, /chat use karo._`);
    }
  }
}

async function handleAIChat(chatId: number, userText: string): Promise<void> {
  const typingMsg = await reply(chatId, "💭 _Soch raha hoon..._").catch(() => null);

  try {
    const aiReply = await chatWithAI(chatId, userText);

    if (typingMsg) {
      await bot!.deleteMessage(chatId, typingMsg.message_id).catch(() => {});
    }

    // Telegram Markdown can break on certain AI output — send in chunks if long
    const MAX_LEN = 3500;
    if (aiReply.length <= MAX_LEN) {
      await reply(chatId, aiReply).catch(() =>
        bot!.sendMessage(chatId, aiReply) // plain if markdown fails
      );
    } else {
      for (let i = 0; i < aiReply.length; i += MAX_LEN) {
        await bot!.sendMessage(chatId, aiReply.slice(i, i + MAX_LEN));
      }
    }
  } catch (err: any) {
    logger.error({ err: err.message, chatId }, "AI chat failed");
    if (typingMsg) await bot!.deleteMessage(chatId, typingMsg.message_id).catch(() => {});
    await reply(chatId, `❌ AI se connect nahi ho pa raha: ${err.message}\n\nDobara try karo ya /errors dekho.`);
  }
}

async function handleBhakti(chatId: number, session: { step: string }, useAI: boolean): Promise<void> {
  if (session.step === "generating") {
    await reply(chatId, "⏳ Ek video pehle se ban rahi hai. Thoda wait karo.");
    return;
  }

  userSessions.set(chatId, { step: "generating" });

  let text: string;
  let textSource: string;

  if (useAI && AI_ENABLED) {
    const thinkingMsg = await reply(chatId, "✨ _AI se bhakti text generate ho raha hai..._");
    try {
      text = await generateBhaktiText();
      await bot!.deleteMessage(chatId, thinkingMsg.message_id).catch(() => {});
      textSource = "AI-generated";
    } catch (err: any) {
      await bot!.deleteMessage(chatId, thinkingMsg.message_id).catch(() => {});
      logger.warn({ err: err.message }, "AI bhakti text failed, using preset");
      text = getNextBhaktiText();
      textSource = "Preset";
    }
  } else {
    text = getNextBhaktiText();
    textSource = "Preset";
  }

  const remaining = getRemainingTopicsCount();
  const statusMsg = await reply(chatId,
    `🙏 *Bhakti Video ban rahi hai...*\n\n` +
    `📖 _${text.slice(0, 100)}..._\n\n` +
    `🎙️ Hindi voice generate ho rahi hai\n` +
    `🖼️ Bhakti images download ho rahi hain\n` +
    `🎬 1 minute video compile ho rahi hai\n\n` +
    `📝 Source: ${textSource}\n` +
    (textSource === "Preset" ? `📚 Topics baaki: ${remaining}\n` : "") +
    `_Please wait... 2-3 minutes_`
  );

  try {
    const jobId = await createVideoJob(text);
    logger.info({ jobId, chatId, useAI, textSource }, "Video job created");
    await pollAndSendVideo(chatId, jobId, statusMsg.message_id);
  } catch (err: any) {
    logger.error({ err: err.message }, "Video job create failed");
    await reply(chatId, `❌ Error: ${err.message}\n\nDobara try karo: /bhakti`);
  } finally {
    userSessions.set(chatId, { step: "idle" });
  }
}

async function handleGenerateVideo(chatId: number, text: string): Promise<void> {
  userSessions.set(chatId, { step: "generating" });

  const statusMsg = await reply(chatId,
    `⏳ *Video ban rahi hai...*\n\n` +
    `🎙️ Hindi voice generate ho rahi hai\n` +
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
  const pollInterval = 5000;
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await sleep(pollInterval);
    const job = getJob(jobId);

    if (!job) {
      await reply(chatId, "❌ Job nahi mili. Dobara try karo: /bhakti");
      return;
    }

    if (job.status === "failed") {
      logger.error({ jobId, error: job.error }, "Job failed");
      await bot!.editMessageText(
        `❌ *Video banane mein error:*\n\`${job.error?.slice(0, 200)}\`\n\nDobara: /bhakti\nDetails: /errors`,
        { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
      ).catch(() => reply(chatId, `❌ Video failed. /errors dekho.`));
      return;
    }

    if (job.status === "done" && job.outputPath && fs.existsSync(job.outputPath)) {
      try {
        await bot!.editMessageText(`✅ *Video ready! Bhej raha hoon...*`,
          { chat_id: chatId, message_id: statusMsgId, parse_mode: "Markdown" }
        ).catch(() => {});

        await bot!.sendVideo(chatId, fs.createReadStream(job.outputPath), {
          caption: `🙏 *Bhakti Video*\n\n${job.text.slice(0, 200)}${job.text.length > 200 ? "..." : ""}`,
          parse_mode: "Markdown",
        });

        logger.info({ chatId, jobId }, "Video sent to Telegram");
        cleanupJob(jobId);
      } catch (err: any) {
        logger.error({ err: err.message, jobId }, "Failed to send video");
        await reply(chatId, `❌ Video bhejna fail hua: ${err.message}`);
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
  await bot!.editMessageText(`⏰ Timeout. Dobara: /bhakti`, { chat_id: chatId, message_id: statusMsgId }).catch(() => {});
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function stopBot(): void {
  if (bot) { bot.stopPolling(); bot = null; logger.info("Telegram bot stopped"); }
}
