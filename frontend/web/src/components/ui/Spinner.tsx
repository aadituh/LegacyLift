export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}
export function Skeleton({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="skeleton" role="status">
      <Spinner /> {label}
    </div>
  );
}
