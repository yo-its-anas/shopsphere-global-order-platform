import { Icon } from "../../../components/Icon";
import type { AlertData } from "../../../types/dashboard";

interface AlertBannerProps {
  alert: AlertData;
  onDismiss: (id: string) => void;
}

export function AlertBanner({ alert, onDismiss }: AlertBannerProps) {
  return (
    <section className={"alert-banner alert-banner--" + alert.tone} role="status">
      <Icon name="alert" size={25} />
      <div>
        <strong>{alert.title}</strong>
        <p>{alert.message}</p>
      </div>
      <button
        aria-label={"Dismiss " + alert.title}
        className="icon-button alert-banner__dismiss"
        onClick={() => onDismiss(alert.id)}
        type="button"
      >
        ×
      </button>
    </section>
  );
}
