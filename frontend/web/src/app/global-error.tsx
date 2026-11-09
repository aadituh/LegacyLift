"use client";
export default function GlobalError({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{ fontFamily: "system-ui", padding: "48px", color: "#102a43" }}
      >
        <h1>LegacyLift couldn’t open.</h1>
        <p>Try loading the application again.</p>
        <button
          onClick={retry}
          style={{ padding: "12px 24px", cursor: "pointer" }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
