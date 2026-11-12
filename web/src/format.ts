export const usd = (n: number, signed = false) => {
  const s = Math.abs(n).toLocaleString("en-US", { style: "currency", currency: "USD" });
  if (!signed) return n < 0 ? `-${s}` : s;
  return n > 0 ? `+${s}` : n < 0 ? `-${s}` : s;
};

export const pct = (n: number | null | undefined, digits = 1) =>
  n == null ? "—" : `${n.toFixed(digits)}%`;

export const cents = (p: number) => `${(p * 100).toFixed(p * 100 % 1 ? 1 : 0)}¢`;

export function timeUntil(iso: string | null, now = Date.now()): string {
  if (!iso) return "unknown";
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return "settling now";
  const h = ms / 3_600_000;
  if (h < 1) return `${Math.max(1, Math.round(ms / 60_000))} min`;
  if (h < 48) return `${Math.round(h)} hr`;
  return `${Math.round(h / 24)} days`;
}

export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "never";
  const min = (now - new Date(iso).getTime()) / 60_000;
  if (min < 1) return "just now";
  if (min < 60) return `${Math.round(min)} min ago`;
  if (min < 48 * 60) return `${Math.round(min / 60)} hr ago`;
  return `${Math.round(min / 1440)} days ago`;
}

export const etTime = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString("en-US", {
        timeZone: "America/New_York",
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }) + " ET"
    : "—";
