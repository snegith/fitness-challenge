/**
 * Title-case a name for display. Presentation only.
 */
export function titleCase(str) {
  if (!str) return "";
  return str.toLowerCase().split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

/**
 * Format a number with commas: 5090 → "5,090"
 */
export function formatNumber(n) {
  return Number(n).toLocaleString();
}

/**
 * Format duration seconds to human-readable: 3661 → "1h 1m"
 */
export function formatDuration(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
