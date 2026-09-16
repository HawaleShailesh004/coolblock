import type { Metadata } from "next";
import { Overpass, Overpass_Mono } from "next/font/google";
import Link from "next/link";
import baselines from "../public/landing/baselines.json";
import scene from "../public/landing/scene.json";
import { BaselineChart, type BaselinesByBudget } from "./_landing/BaselineChart";
import styles from "./_landing/landing.module.css";
import { ScrollStory } from "./_landing/ScrollStory";

/**
 * §9.7 / Phase 12: the marketing homepage (docs/adr/0029-*.md).
 *
 * Every number and image here comes from the real pipeline through
 * scripts/export_landing_scene.py -- the 3D neighborhood, the plan it shows,
 * the pipeline counts and the five-strategy comparison. Nothing is typed in
 * by hand, so re-running the export after the data changes updates the page.
 *
 * Type is Overpass, a descendant of the Highway Gothic lettering on American
 * street signs: the voice of public works, for a tool about city streets.
 */

const overpass = Overpass({ subsets: ["latin"], weight: ["400", "600", "700", "800"], variable: "--font-overpass", display: "swap" });
const overpassMono = Overpass_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-overpass-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CoolBlock: where should the next 40 trees go?",
  description:
    "CoolBlock turns a heat grant into a defensible tree plan: which public sites get trees, what each costs, and who it cools. Real public data for Edison–Eastlake, Phoenix.",
};

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const int = new Intl.NumberFormat("en-US");

const SOURCES = [
  {
    title: "The tree cover and temperature disparity in US urbanized areas: quantifying the association with income across 5,723 communities",
    venue: "PLOS ONE",
    href: "https://doi.org/10.1371/journal.pone.0249715",
  },
  {
    title: "Trees halve urban heat island effect globally but unequal benefits only modestly mitigate climate-change warming",
    venue: "Nature Communications",
    href: "https://doi.org/10.1038/s41467-026-71825-x",
  },
  {
    title: "Increasing tree canopy lowers urban air temperature by up to 1.5 °C in heat-prone areas",
    venue: "npj Urban Sustainability",
    href: "https://doi.org/10.1038/s42949-025-00277-x",
  },
  {
    title: "Street trees provide an opportunity to mitigate urban heat and reduce risk of high heat exposure",
    venue: "Scientific Reports",
    href: "https://doi.org/10.1038/s41598-024-51921-y",
  },
  {
    title: "Urban Heat Equity",
    venue: "American Forests, Tree Equity Score",
    href: "https://www.treeequityscore.org/stories/urban-heat-equity",
  },
];

export default function HomePage() {
  const { plan, counts, frame } = scene;
  const pipeline = [
    { figure: int.format(counts.buildings_mapped), text: "buildings mapped, with every road and parking lot" },
    { figure: int.format(counts.tree_sites_possible), text: "places with room for a tree" },
    { figure: int.format(counts.tree_sites_public), text: "of them on public land a city can plant" },
    { figure: String(counts.vulnerability_factors), text: "heat-risk factors weigh who each tree would cool" },
    { figure: `${plan.trees} trees`, text: `at ${plan.sites} sites for ${usd.format(plan.cost_usd)}` },
  ];

  return (
    <main className={`${overpass.variable} ${overpassMono.variable} ${styles.page}`}>
      <ScrollStory
        numbers={{
          plan,
          counts,
          lstRangeC: frame.lst_range_c as [number, number],
        }}
      />

      <section id="evidence" className="mx-auto max-w-295 px-5 pt-24 pb-20 sm:px-8 sm:pt-32">
        <div className="max-w-160">
          <h2 className={styles.h2}>Same money, five ways to spend it</h2>
          <p className={`${styles.lede} mt-4`} style={{ color: "var(--ink-2)" }}>
            Cities already pick tree sites somehow. We ran the common ways against CoolBlock on the same budget and the
            same public sites, and measured how much cooling reaches the people who need it.
          </p>
        </div>
        <div className="mt-12">
          <BaselineChart data={baselines.by_budget as BaselinesByBudget} />
        </div>
      </section>

      <section className="border-t" style={{ borderColor: "var(--rule)", background: "var(--concrete-2)" }}>
        <div className="mx-auto max-w-295 px-5 py-20 sm:px-8 sm:py-24">
          <h2 className={styles.h2}>How it decides</h2>
          <ol className="mt-12 grid gap-px overflow-hidden rounded-lg sm:grid-cols-5" style={{ background: "var(--rule)" }}>
            {pipeline.map((stage, i) => (
              <li key={stage.text} className="relative p-5 sm:p-6" style={{ background: "var(--concrete-2)" }}>
                <span className="block text-[1.75rem] font-extrabold leading-none tracking-tight sm:text-[2rem]">
                  {stage.figure}
                </span>
                <span className={`${styles.body} mt-3 block text-[0.95rem]`} style={{ color: "var(--ink-2)" }}>
                  {stage.text}
                </span>
                {i < pipeline.length - 1 && (
                  <span
                    aria-hidden
                    className="absolute hidden sm:block"
                    style={{
                      right: -7,
                      top: "50%",
                      width: 13,
                      height: 13,
                      background: "var(--concrete-2)",
                      borderTop: "1px solid var(--rule)",
                      borderRight: "1px solid var(--rule)",
                      transform: "translateY(-50%) rotate(45deg)",
                      zIndex: 1,
                    }}
                  />
                )}
              </li>
            ))}
          </ol>
          <p className={`${styles.body} mt-6 max-w-184 text-[0.95rem]`} style={{ color: "var(--ink-2)" }}>
            The cooling each tree would give is calibrated on this neighborhood’s own temperature readings, not borrowed
            from a national average. Then a solver picks the set of sites that cools the most at-risk people for the
            money — and for a plan this size it proves, in about two seconds, that no other set of sites does better.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-295 gap-14 px-5 py-20 sm:px-8 sm:py-24 lg:grid-cols-2">
        <div>
          <h2 className={styles.h2}>What it can’t tell you</h2>
          <ul className={`${styles.body} mt-8 flex flex-col gap-5`} style={{ color: "var(--ink-2)" }}>
            <li>
              <strong style={{ color: "var(--ink)" }}>It ranks places; it doesn’t forecast degrees.</strong> The heat model
              passed 2 of its 3 validation checks, so treat its numbers as priorities, not promises.
            </li>
            <li>
              <strong style={{ color: "var(--ink)" }}>Trees are only compared with trees.</strong> A cool roof lowers the
              temperature of the roof; a tree cools the air around people. Those aren’t the same measurement, so the app
              never ranks one against the other.
            </li>
            <li>
              <strong style={{ color: "var(--ink)" }}>One neighborhood so far.</strong> Everything here is Edison–Eastlake,
              Phoenix.
            </li>
            <li>
              <strong style={{ color: "var(--ink)" }}>Not modeled yet:</strong> which species to plant, how much water they
              need, and how wind moves cool air down a street.
            </li>
          </ul>
        </div>
        <div>
          <h2 className={styles.h2}>What it stands on</h2>
          <ul className="mt-8 flex flex-col gap-5">
            {SOURCES.map((s) => (
              <li key={s.href}>
                <a href={s.href} className="font-semibold leading-snug underline decoration-1 underline-offset-4 hover:decoration-2">
                  {s.title}
                </a>
                <span className="mt-1 block text-sm" style={{ color: "var(--ink-3)" }}>
                  {s.venue}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section style={{ background: "var(--asphalt)", color: "var(--paper)" }}>
        <div className="mx-auto flex max-w-295 flex-col items-start gap-8 px-5 py-20 sm:px-8 sm:py-24 lg:flex-row lg:items-end lg:justify-between">
          <h2 className={`${styles.h2} max-w-xl`}>Set your own budget and watch the sites get chosen.</h2>
          <Link href="/map" className={styles.buttonOnDark}>
            Open the live plan
          </Link>
        </div>
        <footer className="mx-auto max-w-295 border-t px-5 py-8 text-sm sm:px-8" style={{ borderColor: "var(--asphalt-2)", color: "var(--paper-2)" }}>
          Built for NextStep Hacks 2026. Data from Landsat, Sentinel-2, OpenStreetMap, the US Census Bureau and the CDC.
        </footer>
      </section>
    </main>
  );
}
