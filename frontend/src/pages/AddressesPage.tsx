import { useEffect, useState, type FormEvent } from "react";

import { AsyncState } from "../components/AsyncState";
import { useCustomerApi } from "../features/customers/useCustomerApi";
import type { AddressInput, CustomerAddress } from "../types/customer";

const emptyAddress: AddressInput = {
  label: "",
  recipient_name: "",
  line1: "",
  line2: "",
  city: "",
  region: "",
  postal_code: "",
  country_code: "",
  phone: "",
  is_default: false,
};

function inputFromAddress(address: CustomerAddress): AddressInput {
  return {
    label: address.label,
    recipient_name: address.recipient_name,
    line1: address.line1,
    line2: address.line2,
    city: address.city,
    region: address.region,
    postal_code: address.postal_code,
    country_code: address.country_code,
    phone: address.phone,
    is_default: address.is_default,
  };
}

export function AddressesPage() {
  const api = useCustomerApi();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [draft, setDraft] = useState<AddressInput>(emptyAddress);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<CustomerAddress | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void api
      .listAddresses()
      .then((loaded) => {
        if (active) {
          setError(null);
          setAddresses(loaded);
        }
      })
      .catch((loadError: unknown) => {
        if (active)
          setError(loadError instanceof Error ? loadError.message : "Addresses are unavailable.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api]);

  function startCreate() {
    setDraft({ ...emptyAddress });
    setEditingId(null);
    setShowForm(true);
    setError(null);
  }

  function startEdit(address: CustomerAddress) {
    setDraft(inputFromAddress(address));
    setEditingId(address.id);
    setShowForm(true);
    setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const update = {
        label: draft.label,
        recipient_name: draft.recipient_name,
        line1: draft.line1,
        line2: draft.line2,
        city: draft.city,
        region: draft.region,
        postal_code: draft.postal_code,
        country_code: draft.country_code,
        phone: draft.phone,
      };
      const saved = editingId
        ? await api.updateAddress(editingId, update)
        : await api.createAddress(draft);
      setAddresses((current) => {
        const withoutSaved = current.filter((address) => address.id !== saved.id);
        const normalized = saved.is_default
          ? withoutSaved.map((address) => ({ ...address, is_default: false }))
          : withoutSaved;
        return [saved, ...normalized];
      });
      setShowForm(false);
      setEditingId(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The address could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function setDefault(addressId: string) {
    setError(null);
    try {
      const selected = await api.setDefaultAddress(addressId);
      setAddresses((current) =>
        current.map((address) => ({ ...address, is_default: address.id === selected.id })),
      );
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "The default address could not be changed.",
      );
    }
  }

  async function confirmDelete() {
    if (!deleteCandidate) return;
    setError(null);
    try {
      await api.deleteAddress(deleteCandidate.id);
      setAddresses((current) => current.filter((address) => address.id !== deleteCandidate.id));
      setDeleteCandidate(null);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error ? deleteError.message : "The address could not be deleted.",
      );
    }
  }

  return (
    <div className="customer-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Customers</span>
          <h1>Address Management</h1>
          <p>Add and maintain addresses owned by your authenticated customer profile.</p>
        </div>
        <button className="button button--primary" onClick={startCreate} type="button">
          Add new address
        </button>
      </header>
      {error && (
        <div className="form-alert" role="alert">
          {error}
        </div>
      )}
      {showForm && (
        <section className="panel form-panel address-form-panel">
          <div className="section-heading">
            <h2>{editingId ? "Edit address" : "Add address"}</h2>
          </div>
          <form className="enterprise-form" onSubmit={submit}>
            <div className="form-grid form-grid--three">
              <label>
                Address label
                <input
                  required
                  maxLength={50}
                  value={draft.label}
                  onChange={(event) => setDraft({ ...draft, label: event.target.value })}
                />
              </label>
              <label>
                Recipient name
                <input
                  required
                  maxLength={200}
                  value={draft.recipient_name}
                  onChange={(event) => setDraft({ ...draft, recipient_name: event.target.value })}
                />
              </label>
              <label>
                Phone
                <input
                  type="tel"
                  value={draft.phone ?? ""}
                  onChange={(event) => setDraft({ ...draft, phone: event.target.value || null })}
                />
              </label>
              <label className="form-span-two">
                Address line 1
                <input
                  required
                  maxLength={200}
                  value={draft.line1}
                  onChange={(event) => setDraft({ ...draft, line1: event.target.value })}
                />
              </label>
              <label>
                Address line 2
                <input
                  maxLength={200}
                  value={draft.line2 ?? ""}
                  onChange={(event) => setDraft({ ...draft, line2: event.target.value || null })}
                />
              </label>
              <label>
                City
                <input
                  required
                  maxLength={100}
                  value={draft.city}
                  onChange={(event) => setDraft({ ...draft, city: event.target.value })}
                />
              </label>
              <label>
                Region
                <input
                  maxLength={100}
                  value={draft.region ?? ""}
                  onChange={(event) => setDraft({ ...draft, region: event.target.value || null })}
                />
              </label>
              <label>
                Postal code
                <input
                  required
                  minLength={2}
                  maxLength={20}
                  value={draft.postal_code}
                  onChange={(event) => setDraft({ ...draft, postal_code: event.target.value })}
                />
              </label>
              <label>
                Country code
                <input
                  required
                  minLength={2}
                  maxLength={2}
                  pattern="[A-Za-z]{2}"
                  value={draft.country_code}
                  onChange={(event) =>
                    setDraft({ ...draft, country_code: event.target.value.toUpperCase() })
                  }
                />
              </label>
              {!editingId && (
                <label className="checkbox-field">
                  <input
                    checked={draft.is_default ?? false}
                    type="checkbox"
                    onChange={(event) => setDraft({ ...draft, is_default: event.target.checked })}
                  />
                  Make this the default address
                </label>
              )}
            </div>
            <div className="form-actions">
              <button className="button button--primary" disabled={saving} type="submit">
                {saving ? "Saving…" : "Save address"}
              </button>
              <button
                className="button button--secondary"
                onClick={() => setShowForm(false)}
                type="button"
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading addresses"
          message="Retrieving addresses through the API Gateway."
        />
      ) : addresses.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No addresses yet"
          message="Add an address to support future order fulfilment."
        />
      ) : (
        <div className="address-grid">
          {addresses.map((address) => (
            <article className="address-card panel" key={address.id}>
              <div className="address-card__heading">
                <h2>{address.label}</h2>
                {address.is_default && <span className="default-badge">Default address</span>}
              </div>
              <address>
                <strong>{address.recipient_name}</strong>
                <span>{address.line1}</span>
                {address.line2 && <span>{address.line2}</span>}
                <span>
                  {address.city}
                  {address.region ? `, ${address.region}` : ""} {address.postal_code}
                </span>
                <span>{address.country_code}</span>
                {address.phone && <span className="mono">{address.phone}</span>}
              </address>
              <div className="address-card__actions">
                {!address.is_default && (
                  <button
                    className="button-link"
                    onClick={() => void setDefault(address.id)}
                    type="button"
                  >
                    Set as default
                  </button>
                )}
                <button className="button-link" onClick={() => startEdit(address)} type="button">
                  Edit {address.label}
                </button>
                <button
                  className="button-link button-link--danger"
                  onClick={() => setDeleteCandidate(address)}
                  type="button"
                >
                  Delete {address.label}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {deleteCandidate && (
        <div className="dialog-backdrop" role="presentation">
          <section
            aria-labelledby="delete-address-title"
            aria-modal="true"
            className="confirm-dialog"
            role="dialog"
          >
            <h2 id="delete-address-title">Delete {deleteCandidate.label}?</h2>
            <p>This removes the address from your customer profile.</p>
            <div className="form-actions">
              <button
                className="button button--primary button--danger"
                onClick={() => void confirmDelete()}
                type="button"
              >
                Delete address
              </button>
              <button
                className="button button--secondary"
                onClick={() => setDeleteCandidate(null)}
                type="button"
              >
                Cancel
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
