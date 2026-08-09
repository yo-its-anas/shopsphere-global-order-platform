import { useEffect, useMemo, useState } from "react";

import { AsyncState } from "../components/AsyncState";
import { useAuth } from "../features/auth/useAuth";
import { useCustomerApi } from "../features/customers/useCustomerApi";
import type { CustomerProfile, CustomerStatus } from "../types/customer";

export function CustomerAdministrationPage() {
  const auth = useAuth();
  const api = useCustomerApi();
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void api
      .listCustomers()
      .then((response) => {
        if (active) {
          setError(null);
          setCustomers(response.items);
        }
      })
      .catch((loadError: unknown) => {
        if (active)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Customer administration is unavailable.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized) return customers;
    return customers.filter((customer) =>
      `${customer.first_name} ${customer.last_name} ${customer.email}`
        .toLocaleLowerCase()
        .includes(normalized),
    );
  }, [customers, query]);

  async function changeStatus(customer: CustomerProfile, status: CustomerStatus) {
    setError(null);
    try {
      const updated = await api.changeCustomerStatus(customer.id, status);
      setCustomers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Customer status could not be changed.",
      );
    }
  }

  return (
    <div className="customer-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Authorized operations</span>
          <h1>Customer Administration</h1>
          <p>View customer profiles. Status management is limited to operations administrators.</p>
        </div>
      </header>
      <section className="admin-toolbar panel">
        <label>
          <span className="sr-only">Search customers</span>
          <input
            placeholder="Search customers…"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <span>
          {auth.hasRole("operations_admin") ? "Operations administrator" : "Support read-only"}
        </span>
      </section>
      {error && (
        <div className="form-alert" role="alert">
          {error}
        </div>
      )}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading customers"
          message="Retrieving authorized customer records through the API Gateway."
        />
      ) : filtered.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No customers found"
          message="No customer profiles match the current view."
        />
      ) : (
        <section className="panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Registration date</th>
                  {auth.hasRole("operations_admin") && <th>Administrative action</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      <strong>
                        {customer.first_name} {customer.last_name}
                      </strong>
                      <br />
                      <span className="mono muted">{customer.id}</span>
                    </td>
                    <td className="mono">{customer.email}</td>
                    <td>
                      <span className={`account-status account-status--${customer.status}`}>
                        <i />
                        {customer.status}
                      </span>
                    </td>
                    <td>{new Date(customer.created_at).toLocaleDateString()}</td>
                    {auth.hasRole("operations_admin") && (
                      <td>
                        <label className="status-control">
                          <span className="sr-only">
                            Change status for {customer.first_name} {customer.last_name}
                          </span>
                          <select
                            aria-label={`Change status for ${customer.first_name} ${customer.last_name}`}
                            value={customer.status}
                            onChange={(event) =>
                              void changeStatus(customer, event.target.value as CustomerStatus)
                            }
                          >
                            <option value="active">Active</option>
                            <option value="suspended">Suspended</option>
                            <option value="closed">Closed</option>
                          </select>
                        </label>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
