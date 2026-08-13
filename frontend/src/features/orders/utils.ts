export function formatMoney(currency: string, amount: string): string {
  const numeric = Number(amount);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat(undefined, { style: "currency", currency }).format(numeric)
    : `${currency} ${amount}`;
}

export function formatOrderDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}
