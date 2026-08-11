import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AsyncState } from "../../../components/AsyncState";
import type { CategoryInput, ProductCategory } from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import { CapabilityError, CataloguePageHeader, StatusBadge } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";

const emptyCategory: CategoryInput = {
  name: "",
  slug: "",
  description: "",
  is_active: true,
  parent_id: null,
};

export function CategoriesPage() {
  const api = useCatalogueApi();
  const auth = useAuth();
  const canManage = auth.hasRole("operations_admin");
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [form, setForm] = useState<CategoryInput>(emptyCategory);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setCategories((await api.listCategories(undefined, 0, 100)).items);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  function beginEdit(category: ProductCategory) {
    setEditingId(category.id);
    setForm({
      name: category.name,
      slug: category.slug,
      description: category.description ?? "",
      is_active: category.is_active,
      parent_id: category.parent_id,
    });
    setValidation(null);
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyCategory);
    setValidation(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    setError(null);
    const normalizedSlug = form.slug.trim().toLowerCase();
    if (!form.name.trim() || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(normalizedSlug)) {
      setValidation("Name is required and slug must contain lower-case words separated by dashes.");
      return;
    }
    setSaving(true);
    try {
      const input = { ...form, name: form.name.trim(), slug: normalizedSlug };
      if (editingId) await api.updateCategory(editingId, input);
      else await api.createCategory(input);
      resetForm();
      await load();
    } catch (saveError) {
      setError(saveError);
    } finally {
      setSaving(false);
    }
  }

  const visible = categories.filter((category) =>
    `${category.name} ${category.slug}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Product Categories"
        description="Maintain the governed hierarchy used to organize catalogue products."
      />
      {canManage && (
        <form
          className="panel enterprise-form catalogue-form compact-form"
          onSubmit={(event) => void submit(event)}
        >
          <div className="panel__header">
            <h2>{editingId ? "Edit category" : "Add category"}</h2>
          </div>
          {validation && <div className="form-alert">{validation}</div>}
          {error !== null && <CapabilityError error={error} />}
          <div className="form-grid form-grid--three">
            <label>
              Category name
              <input
                aria-label="Category name"
                maxLength={120}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
                value={form.name}
              />
            </label>
            <label>
              Slug
              <input
                aria-label="Category slug"
                maxLength={80}
                onChange={(event) => setForm({ ...form, slug: event.target.value })}
                required
                value={form.slug}
              />
            </label>
            <label>
              Parent category
              <select
                aria-label="Parent category"
                onChange={(event) => setForm({ ...form, parent_id: event.target.value || null })}
                value={form.parent_id ?? ""}
              >
                <option value="">No parent</option>
                {categories
                  .filter((category) => category.id !== editingId)
                  .map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="form-span-two">
              Description
              <input
                aria-label="Category description"
                maxLength={2000}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                value={form.description}
              />
            </label>
            <label className="checkbox-field">
              <input
                checked={form.is_active}
                onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                type="checkbox"
              />
              Active category
            </label>
          </div>
          <div className="form-actions">
            {editingId && (
              <button className="button button--secondary" onClick={resetForm} type="button">
                Cancel
              </button>
            )}
            <button className="button button--primary" disabled={saving} type="submit">
              {saving ? "Saving…" : editingId ? "Save category" : "Create category"}
            </button>
          </div>
        </form>
      )}

      <div className="panel catalogue-toolbar catalogue-toolbar--single">
        <label>
          <span>Filter categories</span>
          <input
            aria-label="Filter categories"
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Name or slug"
            type="search"
            value={filter}
          />
        </label>
      </div>
      {!canManage && (
        <p className="role-notice">
          Category management is restricted to operations administrators.
        </p>
      )}
      {error !== null && !canManage && <CapabilityError error={error} />}
      {loading ? (
        <AsyncState kind="loading" title="Loading categories" message="Retrieving category data." />
      ) : visible.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No categories found"
          message="No category matches this filter."
        />
      ) : (
        <div className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table catalogue-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Slug</th>
                  <th>Parent</th>
                  <th>Status</th>
                  {canManage && <th aria-label="Actions" />}
                </tr>
              </thead>
              <tbody>
                {visible.map((category) => (
                  <tr key={category.id}>
                    <td>
                      <strong>{category.name}</strong>
                      <small className="table-description">{category.description}</small>
                    </td>
                    <td className="mono-data">{category.slug}</td>
                    <td>
                      {categories.find((candidate) => candidate.id === category.parent_id)?.name ??
                        "—"}
                    </td>
                    <td>
                      <StatusBadge status={category.is_active} />
                    </td>
                    {canManage && (
                      <td className="table-actions">
                        <button
                          className="button-link"
                          onClick={() => beginEdit(category)}
                          type="button"
                        >
                          Edit
                        </button>
                      </td>
                    )}
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
