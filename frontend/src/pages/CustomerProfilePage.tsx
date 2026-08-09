import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AsyncState } from "../components/AsyncState";
import { environment } from "../config/environment";
import { useCustomerApi } from "../features/customers/useCustomerApi";
import type { CustomerProfile, ProfileUpdate } from "../types/customer";

export function CustomerProfilePage() {
  const api = useCustomerApi();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [draft, setDraft] = useState<ProfileUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    try {
      const loaded = await api.getOrProvisionProfile();
      setError(null);
      setProfile(loaded);
      setDraft({
        first_name: loaded.first_name,
        last_name: loaded.last_name,
        email: loaded.email,
        phone: loaded.phone,
      });
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : "The customer profile is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    let active = true;
    void api
      .getOrProvisionProfile()
      .then((loaded) => {
        if (!active) return;
        setError(null);
        setProfile(loaded);
        setDraft({
          first_name: loaded.first_name,
          last_name: loaded.last_name,
          email: loaded.email,
          phone: loaded.phone,
        });
      })
      .catch((loadError: unknown) => {
        if (active)
          setError(
            loadError instanceof Error ? loadError.message : "The customer profile is unavailable.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateProfile(draft);
      setProfile(updated);
      setEditing(false);
    } catch (saveError) {
      setError(
        saveError instanceof Error ? saveError.message : "The profile could not be updated.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading)
    return (
      <div className="customer-page">
        <AsyncState
          kind="loading"
          title="Loading your profile"
          message="Retrieving customer information through the API Gateway."
        />
      </div>
    );
  if (!profile)
    return (
      <div className="customer-page">
        <AsyncState
          kind="error"
          title="Profile unavailable"
          message={error ?? "The customer profile could not be loaded."}
          onRetry={() => {
            setLoading(true);
            void loadProfile();
          }}
        />
      </div>
    );

  return (
    <div className="customer-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Customer Identity</span>
          <h1>My Profile</h1>
          <p>
            Manage your customer-domain information. Authentication remains managed by Keycloak.
          </p>
        </div>
      </header>
      {error && (
        <div className="form-alert" role="alert">
          {error}
        </div>
      )}
      <div className="profile-grid">
        <section className="profile-summary panel">
          <span className="profile-avatar" aria-hidden="true">
            {profile.first_name.charAt(0)}
            {profile.last_name.charAt(0)}
          </span>
          <h2>
            {profile.first_name} {profile.last_name}
          </h2>
          <span className={`account-status account-status--${profile.status}`}>
            <i />
            {profile.status} account
          </span>
          <p className="mono">
            Customer ID
            <br />
            {profile.id}
          </p>
        </section>
        <div className="profile-content">
          <section className="panel form-panel">
            <div className="section-heading">
              <h2>Personal Information</h2>
              {!editing && (
                <button
                  className="button button--primary"
                  onClick={() => setEditing(true)}
                  type="button"
                >
                  Edit profile
                </button>
              )}
            </div>
            {editing ? (
              <form className="enterprise-form" onSubmit={submit}>
                <div className="form-grid">
                  <label>
                    First name
                    <input
                      required
                      maxLength={100}
                      value={draft.first_name ?? ""}
                      onChange={(event) => setDraft({ ...draft, first_name: event.target.value })}
                    />
                  </label>
                  <label>
                    Last name
                    <input
                      required
                      maxLength={100}
                      value={draft.last_name ?? ""}
                      onChange={(event) => setDraft({ ...draft, last_name: event.target.value })}
                    />
                  </label>
                  <label>
                    Email address
                    <input
                      required
                      type="email"
                      value={draft.email ?? ""}
                      onChange={(event) => setDraft({ ...draft, email: event.target.value })}
                    />
                  </label>
                  <label>
                    Phone number
                    <input
                      type="tel"
                      value={draft.phone ?? ""}
                      onChange={(event) =>
                        setDraft({ ...draft, phone: event.target.value || null })
                      }
                    />
                  </label>
                </div>
                <div className="form-actions">
                  <button className="button button--primary" disabled={saving} type="submit">
                    {saving ? "Saving…" : "Save changes"}
                  </button>
                  <button
                    className="button button--secondary"
                    onClick={() => setEditing(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <dl className="detail-grid">
                <div>
                  <dt>First name</dt>
                  <dd>{profile.first_name}</dd>
                </div>
                <div>
                  <dt>Last name</dt>
                  <dd>{profile.last_name}</dd>
                </div>
                <div>
                  <dt>Email address</dt>
                  <dd className="mono">{profile.email}</dd>
                </div>
                <div>
                  <dt>Phone number</dt>
                  <dd>{profile.phone ?? "Not provided"}</dd>
                </div>
              </dl>
            )}
          </section>
          <section className="panel security-panel">
            <div>
              <strong>Identity provider managed</strong>
              <p>
                Sign-in, passwords, sessions, and multi-factor settings are managed securely by
                Keycloak.
              </p>
            </div>
            <a
              className="button button--secondary"
              href={`${environment.keycloak.url}/realms/${encodeURIComponent(environment.keycloak.realm)}/account/`}
            >
              Manage security
            </a>
          </section>
        </div>
      </div>
    </div>
  );
}
