import pino from "pino";
import { captureLog } from "../services/logCapture";

const isProduction = process.env.NODE_ENV === "production";

const baseLogger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  redact: [
    "req.headers.authorization",
    "req.headers.cookie",
    "res.headers['set-cookie']",
  ],
  ...(isProduction
    ? {}
    : {
        transport: {
          target: "pino-pretty",
          options: { colorize: true },
        },
      }),
});

type LogData = Record<string, unknown>;

function extractMsg(args: unknown[]): { msg: string; data?: LogData } {
  if (typeof args[0] === "string") return { msg: args[0] };
  if (typeof args[0] === "object" && args[0] !== null && typeof args[1] === "string") {
    return { msg: args[1], data: args[0] as LogData };
  }
  return { msg: String(args[0] ?? "") };
}

export const logger = new Proxy(baseLogger, {
  get(target, prop) {
    const orig = (target as any)[prop];
    if (prop === "info" || prop === "warn" || prop === "error" || prop === "debug") {
      return (...args: unknown[]) => {
        const { msg, data } = extractMsg(args);
        captureLog(prop as any, msg, data);
        return (orig as Function).apply(target, args);
      };
    }
    return typeof orig === "function" ? orig.bind(target) : orig;
  },
});
