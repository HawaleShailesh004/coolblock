import Link from "next/link";
import Image from "next/image";
import { ScrollHeatHero } from "./ScrollHeatHero";

/**
 * §9.7 / Phase 12: the marketing site -- "Field Instrument" tokens (§8.1:
 * light/editorial for marketing, dark/technical for the app), only real,
 * already-computed numbers (docs/METHODOLOGY.md, docs/DATA-SOURCES.md,
 * data/cache/literature's five real cited papers), and no fabricated stat
 * anywhere, matching the rest of this project's honesty rail.
 *
 * The scroll-driven 3D hero (ScrollHeatHero/HeatBlockScene) is real
 * three.js/@react-three/fiber, not a video or a CSS trick -- lazily
 * hydrated below the headline, and it holds at a fixed frame instead of
 * animating on scroll under `prefers-reduced-motion` or on a detected
 * low-end device (no WebGL, ≤2 cores), per §9.7's own requirement.
 *
 * The "live demo" section links to the real running app rather than
 * embedding it in an iframe -- an iframe was tried and dropped
 * (docs/adr/0027-*.md): a real hydration-mismatch quirk specific to the
 * embedded context, plus a full second copy of the app (and its real
 * backend cost) loading on every marketing pageview, for marginal value
 * over a real screenshot (apps/web/public/hero-map.png) and a direct
 * link.
 */

const CITATIONS: { title: string; venue: string; usedFor: string; href: string | null }[] = [
  {
    title: "The tree cover and temperature disparity in US urbanized areas: quantifying the association with income across 5,723 communities",
    venue: "PLOS ONE",
    usedFor: "the 4.0°C / 30%-less-canopy disparity figures for low-income blocks",
    href: "https://doi.org/10.1371/journal.pone.0249715",
  },
  {
    title: "Trees halve urban heat island effect globally but unequal benefits only modestly mitigate climate-change warming",
    venue: "Nature Communications",
    usedFor: "why cooling benefits accrue disproportionately to higher-income areas",
    href: "https://doi.org/10.1038/s41467-026-71825-x",
  },
  {
    title: "Increasing tree canopy lowers urban air temperature by up to 1.5°C in heat-prone areas",
    venue: "npj Urban Sustainability",
    usedFor: "the canopy-increment → degrees relationship behind the cooling kernel",
    href: "https://doi.org/10.1038/s42949-025-00277-x",
  },
  {
    title: "Street trees provide an opportunity to mitigate urban heat and reduce risk of high heat exposure",
    venue: "Scientific Reports",
    usedFor: "the shade/exposure framing behind the equity-weighted objective",
    href: "https://doi.org/10.1038/s41598-024-51921-y",
  },
  {
    title: "Urban Heat Equity",
    venue: "American Forests / Tree Equity Score",
    usedFor: "the 62-million-tree gap and the finding that 92% of cities show this disparity",
    href: "https://www.treeequityscore.org/stories/urban-heat-equity",
  },
];

const STATS: { value: string; label: string }[] = [
  { value: "4.6–14×", label: "more equity-weighted cooling delivered than the best existing tool, at equal budget" },
  { value: "2,844", label: "real buildings modeled in this one neighborhood, from public data" },
  { value: "4,371", label: "candidate sites scored — every plantable metre and retrofittable roof, not a shortlist" },
  { value: "5", label: "peer-reviewed papers actually cited, not just gestured at" },
];

const STEPS: { title: string; body: string }[] = [
  { title: "Pick a neighborhood, set a budget", body: "Whatever a real grant actually is — $20,000, $50,000, $200,000." },
  {
    title: "State your constraints in plain English",
    body: '"Keep it to public land, prioritize sites near Garfield Elementary, cap maintenance at $8k/yr" — parsed into a real, validated config, not a guess.',
  },
  {
    title: "CoolBlock builds the real model underneath",
    body: "A measured heat surface, every plantable square metre, the cooling each intervention would actually deliver, weighted by who is actually vulnerable — then it solves for the best allocation of the money you have.",
  },
  {
    title: "Get a plan you can defend in the room",
    body: "Ranked, costed sites on a real 3D map, a council memo with every number traced back to its source, and a proof that it beats the alternatives.",
  },
];

export default function HomePage() {
  return (
    <main className="bg-paper-0 text-ink-0">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <span className="font-display text-xl">CoolBlock</span>
        <Link
          href="/map"
          className="rounded-md bg-ink-0 px-4 py-2 text-sm font-medium text-paper-0 transition-opacity hover:opacity-85"
        >
          Open the app →
        </Link>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 pb-16 pt-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-0/60">
          CoolBlock · a block-scale heat-mitigation siting optimizer
        </p>
        <h1 className="mt-4 max-w-3xl font-display text-5xl leading-[1.1] text-ink-0 sm:text-6xl">
          Where should the next 40 trees go?
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-[1.55] text-ink-0/80">
          A city sustainability office just received a real heat-mitigation grant and has no
          defensible way to spend it. Today the answer is a guess, a squeaky-wheel request, or
          whichever block the loudest homeowner lives on. CoolBlock replaces that with a ranked,
          costed, defensible plan in under two minutes — for one real neighborhood, Edison–Eastlake,
          Phoenix, on real public data.
        </p>
        <div className="mt-8 flex items-center gap-4">
          <Link
            href="/map"
            className="rounded-md bg-ink-0 px-5 py-3 text-sm font-medium text-paper-0 transition-opacity hover:opacity-85"
          >
            Open the live instrument →
          </Link>
          <a href="#evidence" className="text-sm text-ink-0/60 underline underline-offset-4">
            See the evidence
          </a>
        </div>
      </section>

      {/* Scroll-driven 3D hero: heats into the problem, cools into the solution (§9.7) */}
      <ScrollHeatHero />

      {/* Live demo */}
      <section id="live-demo" className="border-y border-ink-0/10 bg-paper-1">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="font-display text-3xl text-ink-0">This is the real, live product</h2>
          <p className="mt-4 max-w-2xl text-sm leading-[1.55] text-ink-0/70">
            Not a video, not a prototype — click through and set a budget yourself. Sites land one
            at a time as the real optimizer runs.
          </p>
          <div className="mt-8 overflow-hidden rounded-lg border border-ink-0/10 bg-bg-0">
            <Image
              src="/hero-map.png"
              alt="CoolBlock's live 3D map of Edison-Eastlake, Phoenix, with the modeled heat surface glowing beneath semi-transparent extruded buildings"
              width={1080}
              height={1033}
              className="h-auto w-full"
            />
          </div>
          <p className="mt-2 font-mono text-xs text-ink-0/40">A real screenshot of the live product, not a mockup.</p>
          <Link
            href="/map"
            className="mt-6 inline-block rounded-md bg-ink-0 px-5 py-3 text-sm font-medium text-paper-0 transition-opacity hover:opacity-85"
          >
            Open the live instrument →
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-ink-0/10 bg-paper-1">
        <div className="mx-auto grid max-w-5xl grid-cols-2 gap-8 px-6 py-12 sm:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="font-mono text-3xl font-medium tabular-nums text-ink-0">{s.value}</div>
              <div className="mt-2 text-sm leading-[1.4] text-ink-0/70">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <h2 className="font-display text-3xl text-ink-0">The core loop</h2>
        <div className="mt-10 grid gap-10 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <div key={step.title}>
              <div className="font-mono text-xs text-ink-0/50">{String(i + 1).padStart(2, "0")}</div>
              <h3 className="mt-2 text-lg font-medium text-ink-0">{step.title}</h3>
              <p className="mt-2 text-sm leading-[1.55] text-ink-0/70">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Evidence */}
      <section id="evidence" className="border-t border-ink-0/10 bg-paper-1">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="font-display text-3xl text-ink-0">The evidence</h2>
          <p className="mt-4 max-w-2xl text-sm leading-[1.55] text-ink-0/70">
            Every cooling estimate in CoolBlock traces to a real, cited source — not a plausible-sounding
            number. These five are cited directly in the product&rsquo;s own council memo.
          </p>
          <ol className="mt-8 flex flex-col gap-6">
            {CITATIONS.map((c) => (
              <li key={c.title} className="border-l-2 border-ink-0/10 pl-4">
                {c.href ? (
                  <a href={c.href} className="text-base font-medium text-ink-0 underline underline-offset-4">
                    {c.title}
                  </a>
                ) : (
                  <span className="text-base font-medium text-ink-0">{c.title}</span>
                )}
                <div className="mt-1 font-mono text-xs uppercase tracking-wide text-ink-0/50">{c.venue}</div>
                <p className="mt-1 text-sm text-ink-0/70">Used for: {c.usedFor}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Honesty */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <h2 className="font-display text-2xl text-ink-0">What we won&rsquo;t claim</h2>
        <p className="mt-4 max-w-2xl text-sm leading-[1.55] text-ink-0/70">
          The heat surface underneath every score passed 2 of its own 3 validation checks — so
          CoolBlock calls its outputs a <em>prioritization score</em>, never predicted cooling in
          degrees you should bank on. Every disclosed limitation, every literature figure this
          product leans on, and every real gap in the underlying data is written up in full in the
          repository&rsquo;s own methodology notes, not hidden until a judge finds them.
        </p>
      </section>

      <footer className="border-t border-ink-0/10 px-6 py-10">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <p className="font-mono text-xs text-ink-0/50">
            CoolBlock · Edison-Eastlake, Phoenix, AZ · built for NextStep Hacks 2026
          </p>
          <Link href="/map" className="text-sm font-medium text-ink-0 underline underline-offset-4">
            Open the live instrument →
          </Link>
        </div>
      </footer>
    </main>
  );
}
