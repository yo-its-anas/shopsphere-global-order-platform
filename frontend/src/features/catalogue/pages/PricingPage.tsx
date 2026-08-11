import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { Product, ProductPrice } from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import { CapabilityError, CataloguePageHeader } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatTimestamp } from "../utils";

export function PricingPage() {
  const api = useCatalogueApi();
  const auth = useAuth();
  const canManage = auth.hasRole("operations_admin");
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [prices, setPrices] = useState<ProductPrice[]>([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("product") ?? "");
  const [currency, setCurrency] = useState("USD");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    setError(null);
    try {
      const result = await api.listProducts({ limit: 100, sort_by: "name" });
      setProducts(result.items);
      const initial = selectedId || result.items[0]?.id || "";
      setSelectedId(initial);
      if (initial)
        setPrices((await api.listPrices(initial, canManage || auth.hasRole("support"))).items);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, auth, canManage, selectedId]);

  useEffect(() => {
    void Promise.resolve().then(loadProducts);
  }, [loadProducts]);

  async function selectProduct(productId: string) {
    setSelectedId(productId);
    setSearchParams(productId ? { product: productId } : {});
    setError(null);
    setPrices(
      productId
        ? (await api.listPrices(productId, canManage || auth.hasRole("support"))).items
        : [],
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    setError(null);
    if (
      !selectedId ||
      !/^[A-Z]{3}$/.test(currency) ||
      !/^\d+(?:\.\d{1,4})?$/.test(amount) ||
      Number(amount) <= 0
    ) {
      setValidation("Select a product and enter a positive amount with up to four decimal places.");
      return;
    }
    setSaving(true);
    try {
      await api.setPrice(selectedId, currency, amount);
      setAmount("");
      setPrices((await api.listPrices(selectedId, true)).items);
    } catch (saveError) {
      setError(saveError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Pricing Management"
        description="Review current prices and manage immediately effective currency-specific prices."
      />
      <div className="panel catalogue-toolbar catalogue-toolbar--single">
        <label>
          <span>Product</span>
          <select
            aria-label="Pricing product"
            onChange={(event) => void selectProduct(event.target.value)}
            value={selectedId}
          >
            <option value="">Select a product</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} · {product.sku}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error !== null && <CapabilityError error={error} />}
      {canManage && selectedId && (
        <form className="panel enterprise-form price-form" onSubmit={(event) => void submit(event)}>
          <div className="panel__header">
            <h2>Set effective price</h2>
          </div>
          {validation && <div className="form-alert">{validation}</div>}
          <div className="price-form__fields">
            <label>
              Currency
              <input
                aria-label="Currency"
                maxLength={3}
                onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                value={currency}
              />
            </label>
            <label>
              Amount
              <input
                aria-label="Price amount"
                inputMode="decimal"
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.0000"
                value={amount}
              />
            </label>
            <button className="button button--primary" disabled={saving} type="submit">
              {saving ? "Saving…" : "Update price"}
            </button>
          </div>
        </form>
      )}
      {!canManage && (
        <p className="role-notice">Price updates are restricted to operations administrators.</p>
      )}
      {loading ? (
        <AsyncState kind="loading" title="Loading prices" message="Retrieving pricing data." />
      ) : !selectedId ? (
        <AsyncState
          kind="empty"
          title="No product selected"
          message="Select a product to view pricing."
        />
      ) : prices.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No prices configured"
          message="This product has no active price."
        />
      ) : (
        <div className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table catalogue-table">
              <thead>
                <tr>
                  <th>Currency</th>
                  <th>Amount</th>
                  <th>Effective from</th>
                  <th>Effective to</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((price) => (
                  <tr key={price.id}>
                    <td className="mono-data">{price.currency_code}</td>
                    <td className="mono-data">
                      <strong>{price.amount}</strong>
                    </td>
                    <td>{formatTimestamp(price.effective_from)}</td>
                    <td>{price.effective_to ? formatTimestamp(price.effective_to) : "Current"}</td>
                    <td>{price.is_active ? "Active" : "Historical"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
