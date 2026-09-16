"use client";

import { useId, useState } from "react";
import styles from "./landing.module.css";

/**
 * Same budget, same public tree sites, five ways to choose -- the real
 * numbers from engine.optimize.plan_service.run_baseline_comparison
 * (apps/web/public/landing/baselines.json, scripts/export_landing_scene.py).
 * Rows keep a fixed order across budgets so a strategy never moves when the
 * budget changes; bar colors were run through the dataviz palette validator
 * against the concrete ground.
 */

export type Strategy = "coolblock" | "tes_score_only" | "squeaky_wheel" | "spread_evenly" | "worst_first";
export type BaselinesByBudget = Record<string, Record<Strategy, number>>;

const ROWS: { key: Strategy; label: string; note: string }[] = [
  { key: "coolblock", label: "CoolBlock", note: "Most cooling per dollar for the people most at risk" },
  { key: "tes_score_only", label: "Tree Equity Score ranking", note: "Plant in the blocks with the lowest score first" },
  { key: "squeaky_wheel", label: "Squeaky wheel", note: "Requests weighted toward higher-income blocks" },
  { key: "spread_evenly", label: "Split evenly", note: "The same dollars for every census block group" },
  { key: "worst_first", label: "Hottest spots first", note: "Rank sites by surface temperature alone" },
];

const int = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function niceMax(v: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(v, 1)));
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (step * magnitude >= v) return step * magnitude;
  }
  return 10 * magnitude;
}

export function BaselineChart({ data }: { data: BaselinesByBudget }) {
  const budgets = Object.keys(data).sort((a, b) => Number(a) - Number(b));
  const [budget, setBudget] = useState(budgets[0] ?? "");
  const [hovered, setHovered] = useState<Strategy | null>(null);
  const tableId = useId();

  const values = data[budget];
  if (!values) return null;
  const others = ROWS.filter((r) => r.key !== "coolblock").map((r) => values[r.key]);
  const bestOther = Math.max(...others);
  const multiple = values.coolblock / bestOther;
  const max = niceMax(Math.max(...Object.values(values)));
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max];

  const leads = budgets.map((b) => {
    const row = data[b]!;
    const best = Math.max(...ROWS.filter((r) => r.key !== "coolblock").map((r) => row[r.key]));
    return { budget: b, multiple: row.coolblock / best };
  });
  const narrowest = leads.reduce((a, b) => (b.multiple < a.multiple ? b : a));
  const widest = leads.reduce((a, b) => (b.multiple > a.multiple ? b : a));

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div role="radiogroup" aria-label="Budget" className="inline-flex rounded-full p-1" style={{ background: "var(--concrete-2)" }}>
          {budgets.map((b) => {
            const selected = b === budget;
            return (
              <button
                key={b}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setBudget(b)}
                className={`${styles.figure} min-h-10 rounded-full px-4 text-sm font-semibold`}
                style={{
                  background: selected ? "var(--ink)" : "transparent",
                  color: selected ? "var(--concrete)" : "var(--ink-2)",
                }}
              >
                {usd.format(Number(b))}
              </button>
            );
          })}
        </div>
        <p className="text-right" aria-live="polite">
          <span className="block text-[3.25rem] font-extrabold leading-none tracking-tight">{multiple.toFixed(1)}×</span>
          <span className="mt-1 block text-sm" style={{ color: "var(--ink-3)" }}>
            the cooling of the next-best way, at {usd.format(Number(budget))}
          </span>
        </p>
      </div>

      {/* pr-16 reserves room for the value label at the end of the longest bar;
          gridlines, bars and tick labels all measure against the same content width. */}
      <div className="relative mt-10 pr-16">
        <div aria-hidden className="pointer-events-none absolute top-0 bottom-7 left-0 right-16">
          {ticks.map((t) => (
            <div
              key={t}
              className="absolute top-0 bottom-0 w-px"
              style={{ left: `${(t / max) * 100}%`, background: "var(--rule)" }}
            />
          ))}
        </div>

        <ul className="relative flex flex-col gap-6">
          {ROWS.map((row) => {
            const v = values[row.key];
            const pct = (v / max) * 100;
            const isPlan = row.key === "coolblock";
            const lifted = hovered === row.key;
            return (
              <li
                key={row.key}
                tabIndex={0}
                onPointerEnter={() => setHovered(row.key)}
                onPointerLeave={() => setHovered(null)}
                onFocus={() => setHovered(row.key)}
                onBlur={() => setHovered(null)}
                aria-label={`${row.label}: ${int.format(v)} person-degree-hours`}
                className="relative cursor-default rounded-md outline-offset-4"
              >
                <div className="flex items-baseline justify-between gap-4">
                  <span className={`text-[0.95rem] ${isPlan ? "font-extrabold" : "font-semibold"}`}>{row.label}</span>
                  <span className="hidden text-sm sm:inline" style={{ color: "var(--ink-3)" }}>
                    {row.note}
                  </span>
                </div>
                <div className="relative mt-2 h-5">
                  <div
                    className={`${styles.bar} absolute top-0 left-0 h-5`}
                    style={{
                      width: `max(${pct}%, 2px)`,
                      borderRadius: "0 4px 4px 0",
                      background: isPlan ? "var(--canopy-ink)" : "var(--chart-muted)",
                      filter: lifted ? "brightness(1.12)" : "none",
                    }}
                  />
                  <span
                    className={`${styles.figure} ${styles.barLabel} absolute top-1/2 -translate-y-1/2 text-sm whitespace-nowrap`}
                    style={{ left: `calc(max(${pct}%, 2px) + 0.5rem)`, color: isPlan ? "var(--ink)" : "var(--ink-2)" }}
                  >
                    {int.format(v)}
                  </span>
                </div>
                {lifted && (
                  <div
                    role="tooltip"
                    className="absolute right-0 -top-2 z-10 -translate-y-full rounded-md px-3 py-2 text-left shadow-sm"
                    style={{ background: "var(--ink)", color: "var(--concrete)" }}
                  >
                    <span className={`${styles.figure} block text-base font-medium`}>{int.format(v)}</span>
                    <span className="block text-xs opacity-80">{row.label}, person-degree-hours</span>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <div aria-hidden className={`${styles.figure} relative mt-3 h-4 text-xs`} style={{ color: "var(--ink-3)" }}>
          {ticks.map((t, i) => (
            <span
              key={t}
              className="absolute"
              style={{ left: `${(t / max) * 100}%`, transform: i === 0 ? "none" : i === ticks.length - 1 ? "translateX(-100%)" : "translateX(-50%)" }}
            >
              {int.format(t)}
            </span>
          ))}
        </div>
      </div>

      <p className={`${styles.body} mt-6 max-w-184 text-sm`} style={{ color: "var(--ink-2)" }}>
        Cooling is counted in person-degree-hours: the modeled temperature drop at each home, times the people living
        there and the hours they spend exposed to heat, weighted toward those most at risk. Every strategy spends the
        same budget on the same public-land tree sites. The lead is smallest at {usd.format(Number(narrowest.budget))}{" "}
        ({narrowest.multiple.toFixed(1)}×) and largest at {usd.format(Number(widest.budget))} (
        {widest.multiple.toFixed(1)}×).
      </p>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold underline decoration-2 underline-offset-4">View as table</summary>
        <div className="mt-3 overflow-x-auto">
          <table id={tableId} className={`${styles.figure} w-full min-w-136 border-collapse text-left`}>
            <caption className="sr-only">Person-degree-hours of cooling by strategy and budget</caption>
            <thead>
              <tr style={{ color: "var(--ink-3)" }}>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Strategy
                </th>
                {budgets.map((b) => (
                  <th key={b} scope="col" className="py-2 pr-4 text-right font-medium">
                    {usd.format(Number(b))}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.key} style={{ borderTop: "1px solid var(--rule)" }}>
                  <th scope="row" className="py-2 pr-4 font-medium" style={{ fontFamily: "var(--font-overpass)" }}>
                    {row.label}
                  </th>
                  {budgets.map((b) => (
                    <td key={b} className="py-2 pr-4 text-right">
                      {int.format(data[b]?.[row.key] ?? 0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
