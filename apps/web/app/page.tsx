export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[68ch] flex-col justify-center gap-6 px-6">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-0/60">
        CoolBlock &middot; Phase 0 &middot; Foundations
      </p>
      <h1 className="font-display text-5xl leading-[1.1] text-ink-0">
        Where should the next 40 trees go?
      </h1>
      <p className="text-lg leading-[1.55] text-ink-0/80">
        The data has been public for ten years and the disparity hasn&rsquo;t moved.
        That&rsquo;s not a data problem &mdash; it&rsquo;s an allocation problem. So we
        built the allocator.
      </p>
      <p className="text-sm leading-[1.55] text-ink-0/60">
        This is the repo&rsquo;s foundation commit. The heat surface, the plantable-space
        model, the optimizer, and the live instrument for Edison&ndash;Eastlake, Phoenix
        arrive in the phases that follow &mdash; tracked in{" "}
        <code className="font-mono text-xs">COOLBLOCK-BUILD-PLAN.md</code>.
      </p>
    </main>
  );
}
