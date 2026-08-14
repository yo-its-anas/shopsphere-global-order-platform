import { AsyncState } from "../../../components/AsyncState";
import { Icon } from "../../../components/Icon";
import type { PlatformHealthMetric } from "../../../types/dashboard";

interface PlatformHealthPanelProps {
  metrics: PlatformHealthMetric[];
}

export function PlatformHealthPanel({ metrics }: PlatformHealthPanelProps) {
  return (
    <section className="panel health-panel" aria-labelledby="platform-health-title">
      <header className="panel__header">
        <div>
          <span className="eyebrow">Platform telemetry</span>
          <h2 id="platform-health-title">Platform Health</h2>
        </div>
        <Icon name="health" size={23} />
      </header>

      {metrics.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No health metrics"
          message="Telemetry will appear after observability APIs are integrated."
        />
      ) : (
        <div className="health-list">
          {metrics.map((metric) => (
            <div className="health-metric" key={metric.id}>
              <div className="health-metric__label">
                <strong>{metric.label}</strong>
                <span className={"mono tone-" + metric.tone}>{metric.displayValue}</span>
              </div>
              <div
                aria-label={metric.label + ": " + metric.displayValue}
                aria-valuemax={100}
                aria-valuemin={0}
                aria-valuenow={metric.utilizationPercent}
                className="health-meter"
                role="meter"
              >
                <span
                  className={"tone-bg-" + metric.tone}
                  style={{ width: String(metric.utilizationPercent) + "%" }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
