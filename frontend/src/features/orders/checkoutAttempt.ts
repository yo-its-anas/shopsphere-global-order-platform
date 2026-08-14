import type { ShoppingCart } from "../../types/order";

const STORAGE_KEY = "shopsphere.checkout-attempt";

interface CheckoutAttempt {
  cartId: string;
  cartVersion: number;
  key: string;
}

function newKey(): string {
  return `checkout-${globalThis.crypto.randomUUID()}`;
}

export function checkoutKeyFor(cart: Pick<ShoppingCart, "id" | "version">): string {
  try {
    const value = sessionStorage.getItem(STORAGE_KEY);
    if (value) {
      const existing = JSON.parse(value) as Partial<CheckoutAttempt>;
      if (
        existing.cartId === cart.id &&
        existing.cartVersion === cart.version &&
        typeof existing.key === "string"
      ) {
        return existing.key;
      }
    }
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
  }

  const attempt = { cartId: cart.id, cartVersion: cart.version, key: newKey() };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(attempt));
  return attempt.key;
}

export function clearCheckoutAttempt(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}
