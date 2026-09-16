"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { SceneData } from "./NeighborhoodScene";
import styles from "./landing.module.css";

// three.js stays out of the server render and out of the JS the headline
// needs; the headline (not the canvas) is the page's largest paint.
const NeighborhoodScene = dynamic(() => import("./NeighborhoodScene"), { ssr: false });

const STEPS = 4; // hero, heat, possible sites, the plan

export interface StoryNumbers {
  plan: { budget_usd: number; sites: number; trees: number; cost_usd: number };
  counts: { buildings_mapped: number; tree_sites_public: number };
  lstRangeC: [number, number];
}

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const int = new Intl.NumberFormat("en-US");

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export function ScrollStory({ numbers }: { numbers: StoryNumbers }) {
  const sectionRef = useRef<HTMLElement | null>(null);
  const [story, setStory] = useState(0);
  const [mode, setMode] = useState<"pending" | "3d" | "static">("pending");
  const [reducedMotion, setReducedMotion] = useState(false);
  const [active, setActive] = useState(true);
  const [data, setData] = useState<SceneData | null>(null);

  useEffect(() => {
    // One client-only capability probe: none of this exists during SSR.
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReducedMotion(media.matches);
    setMode(hasWebGL() ? "3d" : "static");
    const onChange = () => setReducedMotion(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (mode !== "3d") return;
    let cancelled = false;
    fetch("/landing/scene.json")
      .then((r) => (r.ok ? (r.json() as Promise<SceneData>) : Promise.reject(new Error(String(r.status)))))
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setMode("static");
      });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        // 0 when the section's top reaches the top of the viewport (the
        // sticky frame is fully on screen), 1 when its end arrives -- the
        // whole range happens while the frame is visible.
        const travel = rect.height - window.innerHeight;
        const p = travel > 0 ? Math.min(1, Math.max(0, -rect.top / travel)) : 0;
        setStory(p * (STEPS - 1));
      });
    };
    const observer = new IntersectionObserver(([entry]) => setActive(Boolean(entry?.isIntersecting)), {
      rootMargin: "100px",
    });
    observer.observe(el);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    onScroll();
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  const current = Math.min(STEPS - 1, Math.round(story));
  const { plan, counts, lstRangeC } = numbers;

  const stepStyle = (i: number) => ({
    opacity: current === i ? 1 : 0,
    transform: reducedMotion || current === i ? "none" : `translateY(${i < current ? -12 : 12}px)`,
    pointerEvents: current === i ? ("auto" as const) : ("none" as const),
  });

  return (
    <section ref={sectionRef} aria-label="Edison–Eastlake, from heat to a tree plan" style={{ height: `${STEPS * 100}svh` }}>
      <div className="sticky top-0 flex h-svh flex-col overflow-hidden" style={{ background: "var(--asphalt)", color: "var(--paper)" }}>
        <header className="relative z-10 mx-auto flex w-full max-w-[1400px] items-center justify-between px-5 py-4 sm:px-8">
          <span className="text-lg font-extrabold tracking-tight">CoolBlock</span>
          <Link href="/map" className="text-sm font-semibold underline decoration-2 underline-offset-4">
            Open the live plan
          </Link>
        </header>

        <div className="relative mx-auto grid w-full max-w-[1400px] flex-1 grid-rows-[1fr_auto] gap-0 lg:grid-cols-[minmax(340px,5fr)_7fr] lg:grid-rows-1">
          {/* Canvas: first on mobile (top), right column on desktop */}
          <div className="relative order-1 min-h-0 lg:order-2">
            {mode === "3d" && data ? (
              <NeighborhoodScene data={data} story={story} reducedMotion={reducedMotion} active={active} />
            ) : mode === "static" ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src="/landing/heat.png"
                alt="Surface temperature map of Edison–Eastlake, Phoenix: hotter streets in orange and yellow, cooler in purple"
                className="h-full w-full object-contain p-6"
              />
            ) : null}
          </div>

          {/* Text steps, stacked in one cell and crossfaded */}
          <div className="relative order-2 grid min-h-[16rem] px-5 pb-8 sm:px-8 lg:order-1 lg:min-h-0 lg:items-center lg:pb-0">
            <div className={`${styles.step} col-start-1 row-start-1 self-center`} style={stepStyle(0)}>
              <h1 className={styles.display}>Where should the next 40 trees go?</h1>
              <p className={`${styles.lede} mt-5 max-w-[34rem]`} style={{ color: "var(--paper-2)" }}>
                CoolBlock turns a heat grant into a plan a city can defend: which public sites get trees, what each one
                costs, and who it cools. Built on real public data for Edison–Eastlake, Phoenix.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-3">
                <Link href="/map" className={styles.buttonOnDark}>
                  Open the live plan
                </Link>
                <a href="#evidence" className="text-sm font-semibold underline decoration-2 underline-offset-4">
                  Skip to the evidence
                </a>
              </div>
              <p className="mt-8 hidden text-sm lg:block" style={{ color: "var(--paper-2)" }}>
                Scroll to watch it decide.
              </p>
            </div>

            <div className={`${styles.step} col-start-1 row-start-1 self-center`} style={stepStyle(1)}>
              <h2 className={styles.stepTitle}>This is the heat</h2>
              <p className={`${styles.lede} mt-4 max-w-[32rem]`} style={{ color: "var(--paper-2)" }}>
                Summer afternoon surface temperature across the neighborhood, measured by 63 Landsat passes and sharpened
                to 10-metre detail by a model.
              </p>
              <div className="mt-6 max-w-[20rem]">
                <div className={styles.heatLegend} role="img" aria-label={`Color scale from ${lstRangeC[0]} to ${lstRangeC[1]} degrees Celsius`} />
                <div className={`${styles.mono} mt-2 flex justify-between text-sm`} style={{ color: "var(--paper-2)" }}>
                  <span>{lstRangeC[0]} °C</span>
                  <span>{lstRangeC[1]} °C</span>
                </div>
              </div>
            </div>

            <div className={`${styles.step} col-start-1 row-start-1 self-center`} style={stepStyle(2)}>
              <h2 className={styles.stepTitle}>A city can plant in {int.format(counts.tree_sites_public)} places</h2>
              <p className={`${styles.lede} mt-4 max-w-[32rem]`} style={{ color: "var(--paper-2)" }}>
                Every public street edge, park and lot with room for a tree. Found by mapping{" "}
                {int.format(counts.buildings_mapped)} buildings, the roads and the parking lots, and keeping the open
                ground that’s left.
              </p>
            </div>

            <div className={`${styles.step} col-start-1 row-start-1 self-center`} style={stepStyle(3)}>
              <h2 className={styles.stepTitle}>
                {usd.format(plan.budget_usd)} plants {plan.trees} trees at these {plan.sites} sites
              </h2>
              <p className={`${styles.lede} mt-4 max-w-[32rem]`} style={{ color: "var(--paper-2)" }}>
                Placed where each dollar of shade reaches the most people at risk from heat: older and very young
                residents, renters, people without a car, and people with asthma or heart disease. Total cost {usd.format(plan.cost_usd)}.
              </p>
              <div className="mt-7">
                <Link href="/map" className={styles.buttonOnDark}>
                  Try your own budget
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
