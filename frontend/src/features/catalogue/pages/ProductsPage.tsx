import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import { ApiClientError } from "../../../services/apiClient";
import type {
  PageResponse,
  Product,
  ProductCardData,
  ProductCategory,
  ProductStatus,
} from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import {
  CapabilityError,
  CataloguePageHeader,
  Pagination,
  ProductLink,
  StatusBadge,
} from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatNumber } from "../utils";

const PAGE_SIZE = 20;

export function ProductsPage() {
  const api = useCatalogueApi();
  const auth = useAuth();
  const [result, setResult] = useState<PageResponse<Product> | null>(null);
  const [cards, setCards] = useState<ProductCardData[]>([]);
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState<ProductStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const canManage = auth.hasRole("operations_admin");
  const canFilterStatus = auth.hasRole("support") || canManage;

  const load = useCallback(async () => {
    setError(null);
    try {
      const [products, categoryPage] = await Promise.all([
        api.listProducts({
          query: query || undefined,
          category_id: categoryId || undefined,
          status: canFilterStatus && status ? status : undefined,
          offset,
          limit: PAGE_SIZE,
          sort_by: "name",
          sort_direction: "asc",
        }),
        api.listCategories(undefined, 0, 100),
      ]);
      const enriched = await Promise.all(
        products.items.map(async (product) => {
          const [priceResult, availabilityResult] = await Promise.allSettled([
            api.listPrices(product.id),
            api.getAvailability(product.id),
          ]);
          const availability =
            availabilityResult.status === "fulfilled"
              ? availabilityResult.value
              : availabilityResult.reason instanceof ApiClientError &&
                  availabilityResult.reason.status === 404
                ? null
                : null;
          return {
            product,
            price:
              priceResult.status === "fulfilled"
                ? (priceResult.value.items.find((item) => item.is_active) ?? null)
                : null,
            availability,
          };
        }),
      );
      setResult(products);
      setCards(enriched);
      setCategories(categoryPage.items);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, canFilterStatus, categoryId, offset, query, status]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setQuery(queryInput.trim());
  }

  const categoryNames = new Map(categories.map((category) => [category.id, category.name]));

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Product Catalogue"
        description="Search governed product records, current pricing, and derived availability."
        actions={
          canManage ? (
            <Link className="button button--primary" to="/products/new">
              Add product
            </Link>
          ) : undefined
        }
      />

      <form className="panel catalogue-toolbar" onSubmit={submitSearch}>
        <label>
          <span>Product search</span>
          <input
            aria-label="Product search"
            maxLength={100}
            onChange={(event) => setQueryInput(event.target.value)}
            placeholder="Search by product name, description, or SKU"
            type="search"
            value={queryInput}
          />
        </label>
        <label>
          <span>Category</span>
          <select
            aria-label="Category filter"
            onChange={(event) => {
              setCategoryId(event.target.value);
              setOffset(0);
            }}
            value={categoryId}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        {canFilterStatus && (
          <label>
            <span>Status</span>
            <select
              aria-label="Product status filter"
              onChange={(event) => {
                setStatus(event.target.value as ProductStatus | "");
                setOffset(0);
              }}
              value={status}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="inactive">Inactive</option>
              <option value="discontinued">Discontinued</option>
            </select>
          </label>
        )}
        <button className="button button--secondary" type="submit">
          Search
        </button>
      </form>

      {error !== null && <CapabilityError error={error} />}
      {loading ? (
        <AsyncState kind="loading" title="Loading products" message="Retrieving catalogue data." />
      ) : cards.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No products found"
          message="Change the search or filter criteria and try again."
        />
      ) : (
        <div className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table catalogue-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Current price</th>
                  <th>Availability</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {cards.map(({ product, price, availability }) => (
                  <tr key={product.id}>
                    <td className="mono-data">{product.sku}</td>
                    <td>
                      <ProductLink id={product.id}>{product.name}</ProductLink>
                    </td>
                    <td>{categoryNames.get(product.category_id) ?? "—"}</td>
                    <td className="mono-data">
                      {price ? `${price.currency_code} ${price.amount}` : "Not set"}
                    </td>
                    <td>
                      {availability ? (
                        <span className="availability-cell">
                          <strong>{formatNumber(availability.quantity_available)}</strong>
                          <StatusBadge status={availability.state} />
                        </span>
                      ) : (
                        "Not initialized"
                      )}
                    </td>
                    <td>
                      <StatusBadge status={product.status} />
                    </td>
                    <td className="table-actions">
                      <Link className="button-link" to={`/products/${product.id}`}>
                        View
                      </Link>
                      {canManage && (
                        <Link className="button-link" to={`/products/${product.id}/edit`}>
                          Edit
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result && (
            <Pagination
              limit={result.limit}
              offset={result.offset}
              onChange={setOffset}
              total={result.total}
            />
          )}
        </div>
      )}
    </section>
  );
}
