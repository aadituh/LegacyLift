export function ConversionProgress({ percent }: { percent?: number }) {
  return (
    <div className="conversion-progress" role="status">
      <strong>Preparing conversion…</strong>
      <p>Preparing the COBOL source for conversion.</p>
      <div
        className={`progress-track ${percent === undefined ? "indeterminate" : ""}`}
        role="progressbar"
        aria-label="Converting"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <span
          style={percent === undefined ? undefined : { width: `${percent}%` }}
        />
      </div>
      {percent !== undefined && <span>{percent}%</span>}
    </div>
  );
}
