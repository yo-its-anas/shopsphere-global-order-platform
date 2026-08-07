import { AsyncState } from "../components/AsyncState";
import { DemoDataBadge } from "../components/DemoDataBadge";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="placeholder-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Day 1 placeholder</span>
          <div className="page-heading__title">
            <h1>{title}</h1>
            <DemoDataBadge />
          </div>
          <p>{description}</p>
        </div>
      </header>
      <AsyncState
        kind="empty"
        title={title + " is not connected"}
        message="Presentation and API integration will be implemented in a later delivery phase."
      />
    </div>
  );
}
