import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { ProductCategory, ProductInput, ProductStatus } from "../../../types/catalogue";
import { CapabilityError, CataloguePageHeader } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";

const initialForm: ProductInput = {
  sku: "",
  name: "",
  description: "",
  category_id: "",
  status: "draft",
  is_searchable: false,
};

export function ProductFormPage() {
  const { productId } = useParams();
  const editing = Boolean(productId);
  const api = useCatalogueApi();
  const navigate = useNavigate();
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [form, setForm] = useState<ProductInput>(initialForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [categoryPage, product] = await Promise.all([
        api.listCategories(true, 0, 100),
        productId ? api.getProduct(productId) : Promise.resolve(null),
      ]);
      setCategories(categoryPage.items);
      if (product) {
        setForm({
          sku: product.sku,
          name: product.name,
          description: product.description ?? "",
          category_id: product.category_id,
          status: product.status,
          is_searchable: product.is_searchable,
        });
      }
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, productId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    setError(null);
    const normalizedSku = form.sku?.trim().toUpperCase() ?? "";
    if (!editing && !/^[A-Z0-9][A-Z0-9._-]+$/.test(normalizedSku)) {
      setValidation(
        "SKU must contain at least two letters, numbers, dots, underscores, or dashes.",
      );
      return;
    }
    if (!form.name.trim() || !form.category_id) {
      setValidation("Product name and category are required.");
      return;
    }
    setSaving(true);
    try {
      const saved = editing
        ? await api.updateProduct(productId!, form)
        : await api.createProduct({ ...form, sku: normalizedSku });
      navigate(`/products/${saved.id}`);
    } catch (saveError) {
      setError(saveError);
    } finally {
      setSaving(false);
    }
  }

  if (loading)
    return (
      <AsyncState kind="loading" title="Loading product form" message="Preparing catalogue data." />
    );

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title={editing ? "Edit product" : "Register product"}
        description="Maintain governed catalogue metadata. SKU becomes immutable after registration."
      />
      <form
        className="panel enterprise-form catalogue-form"
        onSubmit={(event) => void submit(event)}
      >
        {(validation !== null || error !== null) &&
          (validation ? (
            <div className="form-alert" role="alert">
              {validation}
            </div>
          ) : (
            <CapabilityError error={error} />
          ))}
        <div className="form-grid">
          <label>
            SKU
            <input
              aria-label="SKU"
              disabled={editing}
              maxLength={64}
              onChange={(event) => setForm({ ...form, sku: event.target.value })}
              required
              value={form.sku}
            />
          </label>
          <label>
            Product name
            <input
              aria-label="Product name"
              maxLength={200}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
              value={form.name}
            />
          </label>
          <label>
            Category
            <select
              aria-label="Product category"
              onChange={(event) => setForm({ ...form, category_id: event.target.value })}
              required
              value={form.category_id}
            >
              <option value="">Select category</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Lifecycle status
            <select
              aria-label="Lifecycle status"
              onChange={(event) =>
                setForm({ ...form, status: event.target.value as ProductStatus })
              }
              value={form.status}
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="discontinued">Discontinued</option>
            </select>
          </label>
          <label className="form-span-two">
            Description
            <textarea
              aria-label="Product description"
              maxLength={2000}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              rows={5}
              value={form.description}
            />
          </label>
          <label className="checkbox-field">
            <input
              checked={form.is_searchable}
              onChange={(event) => setForm({ ...form, is_searchable: event.target.checked })}
              type="checkbox"
            />
            Searchable in customer catalogue
          </label>
        </div>
        <div className="form-actions">
          <Link
            className="button button--secondary"
            to={productId ? `/products/${productId}` : "/products"}
          >
            Cancel
          </Link>
          <button className="button button--primary" disabled={saving} type="submit">
            {saving ? "Saving…" : editing ? "Save changes" : "Register product"}
          </button>
        </div>
      </form>
    </section>
  );
}
