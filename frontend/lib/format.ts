/**
 * Formats a rupee amount without hiding paise: whole amounts show no decimals
 * (₹40), fractional amounts show two (₹60.50). Never rounds to the nearest rupee.
 */
export function formatPrice(value: number | string | null | undefined): string {
  const amount = typeof value === "number" ? value : parseFloat(String(value ?? ""));
  if (!Number.isFinite(amount)) return "0";
  return Number.isInteger(amount) ? amount.toFixed(0) : amount.toFixed(2);
}
