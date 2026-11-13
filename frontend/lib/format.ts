/**
 * Formats a rupee amount without hiding paise: whole amounts show no decimals
 * (₹40), fractional amounts show two (₹60.50). Never rounds to the nearest rupee.
 */
export function formatPrice(value: number | string | null | undefined): string {
  const amount = typeof value === "number" ? value : parseFloat(String(value ?? ""));
  if (!Number.isFinite(amount)) return "0";
  return Number.isInteger(amount) ? amount.toFixed(0) : amount.toFixed(2);
}

/**
 * Turns whatever a person types or pastes into a 10-digit Indian mobile number.
 * "919876543210", "+91 98765 43210" and "09876543210" all become "9876543210";
 * the country prefix is stripped, never kept as part of the number.
 */
export function normalizeIndianMobileInput(raw: string): string {
  let digits = String(raw ?? "").replace(/\D/g, "");
  if (digits.length > 10 && digits.startsWith("91")) digits = digits.slice(2);
  if (digits.length > 10 && digits.startsWith("0")) digits = digits.replace(/^0+/, "");
  return digits.slice(0, 10);
}
