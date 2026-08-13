import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import { ApiClientError } from "../../../services/apiClient";
import type { InventoryItem, InventoryMovementType, Product } from "../../../types/catalogue";
import { CapabilityError, CataloguePageHeader, StatusBadge } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { createIdempotencyKey, formatNumber } from "../utils";

type AdjustableMovement = Exclude<InventoryMovementType, "INITIAL_STOCK">;

export function InventoryAdjustmentPage() {
  const { productId = "" } = useParams();
  const api = useCatalogueApi();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [inventory, setInventory] = useState<InventoryItem | null>(null);
  const [movementType, setMovementType] = useState<AdjustableMovement>("STOCK_RECEIPT");
  const [quantity, setQuantity] = useState("1");
  const [threshold, setThreshold] = useState("0");
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const loadedProduct = await api.getProduct(productId);
      const loadedInventory = await api.getInventory(productId).catch((inventoryError: unknown) => {
        if (inventoryError instanceof ApiClientError && inventoryError.status === 404) return null;
        throw inventoryError;
      });
      setProduct(loadedProduct);
      setInventory(loadedInventory);
      if (loadedInventory) setThreshold(String(loadedInventory.reorder_threshold));
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, productId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  function requestConfirmation(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    const amount = Number(quantity);
    if (!Number.isInteger(amount) || amount === 0 || !reason.trim() || reason.trim().length < 3) {
      setValidation(
        "Enter a non-zero whole-unit quantity and a reason of at least three characters.",
      );
      return;
    }
    if (!inventory && amount < 0) {
      setValidation("Initial quantity cannot be negative.");
      return;
    }
    setConfirming(true);
  }

  function normalizedDelta(): number {
    const magnitude = Math.abs(Number(quantity));
    if (movementType === "DAMAGE") return -magnitude;
    if (movementType === "STOCK_RECEIPT") return magnitude;
    return Number(quantity);
  }

  async function confirmAdjustment() {
    setSaving(true);
    setError(null);
    try {
      if (inventory) {
        await api.adjustInventory(productId, {
          movement_type: movementType,
          quantity_delta: normalizedDelta(),
          reason: reason.trim(),
          reference: reference.trim() || undefined,
          idempotency_key: createIdempotencyKey("inventory-adjustment"),
          expected_version: inventory.version,
        });
      } else {
        await api.initializeInventory(productId, {
          quantity_on_hand: Number(quantity),
          reorder_threshold: Number(threshold),
          reason: reason.trim(),
          reference: reference.trim() || undefined,
          idempotency_key: createIdempotencyKey("inventory-initialization"),
        });
      }
      navigate(`/inventory/${productId}/movements`);
    } catch (saveError) {
      setError(saveError);
      setConfirming(false);
    } finally {
      setSaving(false);
    }
  }

  if (loading)
    return (
      <AsyncState
        kind="loading"
        title="Loading inventory"
        message="Retrieving current stock state."
      />
    );
  if (error !== null && !product) return <CapabilityError error={error} />;

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title={inventory ? "Record Inventory Adjustment" : "Initialize Inventory"}
        description="Every submitted stock change creates an append-only movement record."
      />
      {product && (
        <article className="panel adjustment-product-summary">
          <div>
            <span>Product</span>
            <strong>{product.name}</strong>
          </div>
          <div>
            <span>SKU</span>
            <strong className="mono-data">{product.sku}</strong>
          </div>
          {inventory && (
            <>
              <div>
                <span>On hand</span>
                <strong>{formatNumber(inventory.quantity_on_hand)}</strong>
              </div>
              <div>
                <span>Available</span>
                <strong>{formatNumber(inventory.quantity_available)}</strong>
              </div>
              <StatusBadge status={inventory.state} />
            </>
          )}
        </article>
      )}
      <form className="panel enterprise-form catalogue-form" onSubmit={requestConfirmation}>
        {validation && (
          <div className="form-alert" role="alert">
            {validation}
          </div>
        )}
        {error !== null && <CapabilityError error={error} />}
        <div className="form-grid">
          {inventory ? (
            <label>
              Movement type
              <select
                aria-label="Movement type"
                onChange={(event) => setMovementType(event.target.value as AdjustableMovement)}
                value={movementType}
              >
                <option value="STOCK_RECEIPT">Stock receipt</option>
                <option value="DAMAGE">Damage</option>
                <option value="MANUAL_ADJUSTMENT">Manual adjustment</option>
                <option value="CORRECTION">Correction</option>
              </select>
            </label>
          ) : (
            <label>
              Reorder threshold
              <input
                aria-label="Reorder threshold"
                min="0"
                onChange={(event) => setThreshold(event.target.value)}
                type="number"
                value={threshold}
              />
            </label>
          )}
          <label>
            {inventory ? "Quantity delta" : "Initial quantity on hand"}
            <input
              aria-label="Adjustment quantity"
              onChange={(event) => setQuantity(event.target.value)}
              step="1"
              type="number"
              value={quantity}
            />
            <small>
              {inventory && movementType === "DAMAGE"
                ? "Entered as units damaged; submitted as a negative delta."
                : "Whole units only."}
            </small>
          </label>
          <label className="form-span-two">
            Reason
            <textarea
              aria-label="Adjustment reason"
              maxLength={500}
              onChange={(event) => setReason(event.target.value)}
              required
              rows={3}
              value={reason}
            />
          </label>
          <label className="form-span-two">
            Reference
            <input
              aria-label="Adjustment reference"
              maxLength={120}
              onChange={(event) => setReference(event.target.value)}
              placeholder="Purchase order, incident, or ticket reference"
              value={reference}
            />
          </label>
        </div>
        <div className="form-actions">
          <Link className="button button--secondary" to="/inventory">
            Cancel
          </Link>
          <button className="button button--primary" type="submit">
            Review adjustment
          </button>
        </div>
      </form>
      {confirming && (
        <div className="dialog-backdrop" role="presentation">
          <section
            aria-labelledby="inventory-confirm-title"
            aria-modal="true"
            className="confirm-dialog"
            role="dialog"
          >
            <h2 id="inventory-confirm-title">Confirm stock change</h2>
            <p>
              This action changes authoritative inventory and creates an immutable movement record.
            </p>
            <dl className="confirmation-summary">
              <div>
                <dt>Product</dt>
                <dd>{product?.name}</dd>
              </div>
              <div>
                <dt>Quantity change</dt>
                <dd className="mono-data">{inventory ? normalizedDelta() : Number(quantity)}</dd>
              </div>
              <div>
                <dt>Reason</dt>
                <dd>{reason}</dd>
              </div>
            </dl>
            <div className="form-actions">
              <button
                className="button button--secondary"
                disabled={saving}
                onClick={() => setConfirming(false)}
                type="button"
              >
                Go back
              </button>
              <button
                className="button button--primary"
                disabled={saving}
                onClick={() => void confirmAdjustment()}
                type="button"
              >
                {saving ? "Submitting…" : "Confirm adjustment"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
