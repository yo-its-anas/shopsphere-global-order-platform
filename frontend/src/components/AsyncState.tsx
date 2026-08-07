interface AsyncStateProps {
  kind: "loading" | "empty" | "error";
  title: string;
  message: string;
  onRetry?: () => void;
}

export function AsyncState({ kind, title, message, onRetry }: AsyncStateProps) {
  return (
    <section className={"async-state async-state--" + kind} aria-live="polite">
      {kind === "loading" && <span className="spinner" aria-hidden="true" />}
      <div>
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
      {kind === "error" && onRetry && (
        <button className="button button--secondary" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </section>
  );
}
