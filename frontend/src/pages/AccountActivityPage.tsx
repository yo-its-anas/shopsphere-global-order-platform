import { useCallback, useEffect, useState } from "react";

import { AsyncState } from "../components/AsyncState";
import { useCustomerApi } from "../features/customers/useCustomerApi";
import type { ActivityEvent } from "../types/customer";

const forbiddenContextKeys = /token|password|secret|credential|session|authorization/i;

function safeContext(event: ActivityEvent): string {
  return (
    Object.entries(event.context)
      .filter(
        ([key, value]) =>
          !forbiddenContextKeys.test(key) && ["string", "number", "boolean"].includes(typeof value),
      )
      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
      .join(" · ") || "No additional context"
  );
}

export function AccountActivityPage() {
  const api = useCustomerApi();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const limit = 25;

  const loadActivity = useCallback(async () => {
    try {
      const response = await api.listOwnActivity(offset, limit);
      setError(null);
      setEvents(response.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Account activity is unavailable.");
    } finally {
      setLoading(false);
    }
  }, [api, offset]);

  useEffect(() => {
    let active = true;
    void api
      .listOwnActivity(offset, limit)
      .then((response) => {
        if (active) {
          setError(null);
          setEvents(response.items);
        }
      })
      .catch((loadError: unknown) => {
        if (active)
          setError(
            loadError instanceof Error ? loadError.message : "Account activity is unavailable.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api, offset]);

  return (
    <div className="customer-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Customer Identity</span>
          <h1>Account Activity</h1>
          <p>Safe customer-domain and authentication activity normalized by customer-service.</p>
        </div>
      </header>
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading account activity"
          message="Retrieving normalized events through the API Gateway."
        />
      ) : error ? (
        <AsyncState
          kind="error"
          title="Activity unavailable"
          message={error}
          onRetry={() => {
            setLoading(true);
            void loadActivity();
          }}
        />
      ) : events.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No activity found"
          message="No activity is available for this page."
        />
      ) : (
        <section className="panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Result</th>
                  <th>Action</th>
                  <th>Category</th>
                  <th>Source</th>
                  <th>Timestamp (UTC)</th>
                  <th>Safe context</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, index) => (
                  <tr key={`${event.timestamp}-${event.action}-${index}`}>
                    <td>
                      <span className={`status result-${event.result}`}>
                        <i className="status__dot" />
                        {event.result}
                      </span>
                    </td>
                    <td>
                      <strong>{event.action.replaceAll("_", " ")}</strong>
                    </td>
                    <td>{event.event_category.replaceAll("_", " ")}</td>
                    <td>{event.source}</td>
                    <td className="mono">
                      {new Date(event.timestamp).toLocaleString(undefined, { timeZone: "UTC" })}
                    </td>
                    <td className="activity-context">{safeContext(event)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <footer className="pagination">
            <span>
              Showing {offset + 1}–{offset + events.length}
            </span>
            <div>
              <button
                className="button button--secondary"
                disabled={offset === 0}
                onClick={() => {
                  setLoading(true);
                  setOffset(Math.max(0, offset - limit));
                }}
                type="button"
              >
                Previous
              </button>
              <button
                className="button button--secondary"
                disabled={events.length < limit}
                onClick={() => {
                  setLoading(true);
                  setOffset(offset + limit);
                }}
                type="button"
              >
                Next
              </button>
            </div>
          </footer>
        </section>
      )}
    </div>
  );
}
