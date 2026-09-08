import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[68ch] flex-col justify-center gap-6 px-6">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-0/60">CoolBlock &middot; 404</p>
      <h1 className="font-display text-5xl leading-[1.1] text-ink-0">This page doesn&rsquo;t exist.</h1>
      <p className="text-lg leading-[1.55] text-ink-0/80">
        The link may be stale, or the address was mistyped. The plan and every solved scenario live
        under <code className="font-mono text-sm">/map</code>.
      </p>
      <p className="text-sm leading-[1.55] text-ink-0/60">
        <Link href="/map" className="underline underline-offset-4">
          Go to the map &rarr;
        </Link>
      </p>
    </main>
  );
}
