"use client";

/**
 * Catches an exception in `RootLayout` itself (the one case `error.tsx`
 * can't -- a layout crash takes its own child error boundary down with
 * it), so a judge never sees a blank white tab. Must render its own
 * `<html>/<body>` since the real root layout is what's broken.
 */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#fff", color: "#111" }}>
        <main style={{ maxWidth: "68ch", margin: "0 auto", padding: "0 24px", minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", gap: 24 }}>
          <h1 style={{ fontSize: 32, lineHeight: 1.1 }}>CoolBlock hit an unexpected error.</h1>
          <p style={{ fontSize: 18, lineHeight: 1.55, opacity: 0.8 }}>
            Reloading usually recovers this. Nothing you did caused it, and nothing was lost.
          </p>
          <button
            onClick={reset}
            style={{ width: "fit-content", borderRadius: 6, border: "1px solid rgba(0,0,0,0.2)", padding: "8px 16px", fontSize: 14, cursor: "pointer", background: "none" }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
