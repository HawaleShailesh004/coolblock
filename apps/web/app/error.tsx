"use client";

import { useEffect } from "react";

/**
 * §1.2's "Typed error states with a recovery action" (Phase 13's own
 * DoD: "Error-boundary coverage on every route; a real 404 and 500") --
 * this catches a render-time exception anywhere under the root layout
 * and offers `reset()` (Next.js's own re-render-the-segment action)
 * rather than leaving the visitor at a blank page or Next's unstyled
 * default. Does not catch errors in `RootLayout` itself -- that's
 * `global-error.tsx`'s job, since a layout crash takes this file down
 * with it.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-[68ch] flex-col justify-center gap-6 px-6">
      <p className="font-mono text-xs uppercase tracking-widest text-warn">CoolBlock &middot; something broke</p>
      <h1 className="font-display text-4xl leading-[1.1] text-ink-0">This view hit an error.</h1>
      <p className="text-lg leading-[1.55] text-ink-0/80">
        Nothing was lost -- your plan and any solved scenario are saved server-side. Retrying usually
        recovers this.
      </p>
      <button
        onClick={reset}
        className="w-fit rounded-md border border-ink-0/20 px-4 py-2 text-sm font-medium text-ink-0 hover:bg-ink-0/5"
      >
        Try again
      </button>
    </main>
  );
}
