import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "—";
  const diffMs = Date.now() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);
  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  if (diffDay < 30) return `${Math.floor(diffDay / 7)}w ago`;
  return formatDate(d);
}

export function formatCurrency(amount: number | null | undefined, currency = "INR"): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600 dark:text-green-400";
  if (score >= 65) return "text-blue-600 dark:text-blue-400";
  if (score >= 50) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

export function scoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-500/15 text-green-700 dark:text-green-300 border-green-500/30";
  if (score >= 65) return "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30";
  if (score >= 50) return "bg-yellow-500/15 text-yellow-700 dark:text-yellow-300 border-yellow-500/30";
  return "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30";
}

export function recommendationColor(rec: string | null | undefined): string {
  const r = (rec || "").toLowerCase();
  if (r.includes("strong") || r.includes("apply")) return "bg-green-500/15 text-green-700 dark:text-green-300 border-green-500/30";
  if (r.includes("good") || r.includes("worth")) return "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30";
  if (r.includes("maybe") || r.includes("stretch")) return "bg-yellow-500/15 text-yellow-700 dark:text-yellow-300 border-yellow-500/30";
  if (r.includes("skip") || r.includes("no")) return "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30";
  return "bg-gray-500/15 text-gray-700 dark:text-gray-300 border-gray-500/30";
}

export function statusColor(status: string | null | undefined): string {
  const s = (status || "").toLowerCase();
  if (s.includes("discovered")) return "bg-slate-500/15 text-slate-700 dark:text-slate-300 border-slate-500/30";
  if (s.includes("shortlist")) return "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30";
  if (s.includes("ready")) return "bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-500/30";
  if (s.includes("applied")) return "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30";
  if (s.includes("interview")) return "bg-violet-500/15 text-violet-700 dark:text-violet-300 border-violet-500/30";
  if (s.includes("offer")) return "bg-green-500/15 text-green-700 dark:text-green-300 border-green-500/30";
  if (s.includes("reject")) return "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30";
  if (s.includes("withdrawn")) return "bg-gray-500/15 text-gray-700 dark:text-gray-300 border-gray-500/30";
  return "bg-gray-500/15 text-gray-700 dark:text-gray-300 border-gray-500/30";
}

export function truncate(str: string, n: number): string {
  if (!str) return "";
  return str.length > n ? str.slice(0, n - 1) + "…" : str;
}

export function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
