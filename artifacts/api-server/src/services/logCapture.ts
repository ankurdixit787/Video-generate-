type LogLevel = "info" | "warn" | "error" | "debug";

interface LogEntry {
  time: string;
  level: LogLevel;
  msg: string;
  data?: string;
}

const MAX_LOGS = 200;
const logs: LogEntry[] = [];

export function captureLog(level: LogLevel, msg: string, data?: Record<string, unknown>): void {
  const entry: LogEntry = {
    time: new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false }),
    level,
    msg,
    data: data ? JSON.stringify(data).slice(0, 200) : undefined,
  };
  logs.push(entry);
  if (logs.length > MAX_LOGS) logs.shift();
}

export function getRecentLogs(count = 30, levelFilter?: LogLevel): LogEntry[] {
  let filtered = levelFilter ? logs.filter((l) => l.level === levelFilter) : logs;
  return filtered.slice(-count);
}

export function getErrorLogs(count = 20): LogEntry[] {
  return logs.filter((l) => l.level === "error" || l.level === "warn").slice(-count);
}

export function formatLogsForTelegram(entries: LogEntry[]): string {
  if (entries.length === 0) return "✅ Koi logs nahi hain.";
  return entries
    .map((e) => {
      const icon = e.level === "error" ? "❌" : e.level === "warn" ? "⚠️" : e.level === "debug" ? "🔍" : "ℹ️";
      const data = e.data ? `\n   └ ${e.data}` : "";
      return `${icon} [${e.time}] ${e.msg}${data}`;
    })
    .join("\n");
}

export function clearLogs(): void {
  logs.length = 0;
}
