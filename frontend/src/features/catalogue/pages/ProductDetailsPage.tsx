import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import { ApiClientError } from "../../../services/apiClient";
import type {
  Product,
  ProductAvailability,
  ProductCategory,
  ProductPrice,
} from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import { CapabilityError, CataloguePageHeader, StatusBadge } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatNumber, formatTimestamp } from "../utils";

export function ProductDetailsPage() {
  const { productId = "" } = useParams();
  const api = useCatalogueApi();
  const auth = useAuth();
  const [product, setProduct] = useState<Product | null>(null);
  const [category, setCategory] = useState<ProductCategory | null>(null);
  const [prices, setPrices] = useState<ProductPrice[]>([]);
  const [availability, setAvailability] = useState<ProductAvailability | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const canManage = auth.hasRole("operations_admin");
  const canReadOperations = auth.hasRole("support") || canManage;

  const load = useCallback(async () => {
    setError(null);
    try {
      const loadedProduct = await api.getProduct(productId);
      const [loadedCategory, loadedPrices, loadedAvailability] = await Promise.all([
        api.getCategory(loadedProduct.category_id),
        api.listPrices(productId),
        api.getAvailability(productId).catch((availabilityError: unknown) => {
          if (availabilityError instanceof ApiClientError && availabilityError.status === 404)
            return null;
          throw availabilityError;
        }),
      ]);
      setProduct(loadedProduct);
      setCategory(loadedCategory);
      setPrices(loadedPrices.items);
      setAvailability(loadedAvailability);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, productId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  if (loading)
    return (
      <AsyncState kind="loading" title="Loading product" message="Retrieving product details." />
    );
  if (error) return <CapabilityError error={error} />;
  if (!product)
    return <AsyncState kind="empty" title="Product not found" message="No product was returned." />;

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title={product.name}
        description={`SKU ${product.sku}`}
        actions={
          <>
            <Link className="button button--secondary" to="/products">
              Back to catalogue
            </Link>
            {canManage && (
              <Link className="button button--primary" to={`/products/${product.id}/edit`}>
                Edit product
              </Link>
            )}
          </>
        }
      />

      <div className="catalogue-detail-grid">
        <article className="panel detail-card detail-card--wide">
          <div className="panel__header">
            <h2>Core information</h2>
            <StatusBadge status={product.status} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Product name</dt>
              <dd>{product.name}</dd>
            </div>
            <div>
              <dt>SKU</dt>
              <dd className="mono-data">{product.sku}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{category?.name ?? "—"}</dd>
            </div>
            <div>
              <dt>Searchable</dt>
              <dd>{product.is_searchable ? "Yes" : "No"}</dd>
            </div>
            <div className="detail-span-two">
              <dt>Description</dt>
              <dd>{product.description ?? "No description provided."}</dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd>{formatTimestamp(product.updated_at)}</dd>
            </div>
          </dl>
        </article>

        <article className="panel detail-card">
          <div className="panel__header">
            <h2>Current pricing</h2>
            <Link className="button-link" to={`/pricing?product=${product.id}`}>
              Pricing view
            </Link>
          </div>
          {prices.length === 0 ? (
            <p className="muted-copy">No active price is configured.</p>
          ) : (
            <div className="price-list">
              {prices.map((price) => (
                <div key={price.id}>
                  <span>{price.currency_code}</span>
                  <strong className="mono-data">{price.amount}</strong>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel detail-card">
          <div className="panel__header">
            <h2>Availability</h2>
            {availability && <StatusBadge status={availability.state} />}
          </div>
          {availability ? (
            <>
              <p className="detail-metric">{formatNumber(availability.quantity_available)}</p>
              <p className="muted-copy">
                Available units as of {formatTimestamp(availability.as_of)}
              </p>
            </>
          ) : (
            <p className="muted-copy">Inventory has not been initialized for this product.</p>
          )}
          {canReadOperations && (
            <div className="card-actions">
              <Link className="button-link" to={`/inventory/${product.id}/movements`}>
                Movement history
              </Link>
              {canManage && (
                <Link className="button-link" to={`/inventory/${product.id}/adjust`}>
                  Adjust inventory
                </Link>
              )}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
