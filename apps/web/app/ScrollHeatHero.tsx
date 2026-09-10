"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

// Lazily hydrated, below the fold of the hero's own headline (§9.7: "3D
// lazily hydrated below the fold and skipped entirely under reduced-motion
// or on low-end devices") -- `ssr: false` keeps three.js/@react-three/fiber
// out of the server render and out of the initial JS the header/headline
// need, since nothing above this component depends on WebGL at all.
const HeatBlockScene = dynamic(() => import("./HeatBlockScene"), { ssr: false });

const STATIC_PROGRESS = 0.35; // a fixed, already-warm-but-not-peak frame for the no-motion/low-end fallback

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function isLowEndDevice(): boolean {
  if (typeof navigator === "undefined") return false;
  const cores = navigator.hardwareConcurrency ?? 4;
  if (cores <= 2) return true;
  try {
    const canvas = document.createElement("canvas");
    return !(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return true;
  }
}

export function ScrollHeatHero() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [progress, setProgress] = useState(STATIC_PROGRESS);
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion() || isLowEndDevice()) return; // stays static at STATIC_PROGRESS, canvas still renders once
    // A one-time client-only capability probe (matchMedia, hardwareConcurrency,
    // WebGL) -- there is no prop/state this could be derived from during
    // render instead, and it must run after mount since `window` doesn't
    // exist during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLive(true);

    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const el = containerRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const viewportH = window.innerHeight;
        // 0 when the container's top just enters the bottom of the
        // viewport, 1 when its bottom leaves the top -- a plain linear
        // scroll-through-container progress, not a physics/spring value
        // (§8.4: numbers tick with useSpring, but this drives a shader-ish
        // color, not a displayed figure).
        const total = rect.height - viewportH;
        const traveled = viewportH - rect.top;
        const p = total > 0 ? traveled / total : 0;
        setProgress(Math.min(1, Math.max(0, p)));
      });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative" style={{ height: "220vh" }}>
      <div className="sticky top-0 flex h-screen flex-col justify-center gap-10 overflow-hidden">
        <div className="mx-auto grid max-w-5xl gap-8 px-6 sm:grid-cols-[1fr_1.1fr] sm:items-center">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-0/50">
              {live ? (progress < 0.5 ? "the problem" : "the solution") : "edison-eastlake, phoenix"}
            </p>
            <p className="mt-3 max-w-sm text-base leading-[1.55] text-ink-0/70">
              {live && progress < 0.45
                ? "A real neighborhood, heating up the same way every summer — while the money to fix it sits unspent."
                : "CoolBlock finds where a dollar of shade actually cools the people who need it most, and the block cools in place."}
            </p>
          </div>
          <div className="aspect-square w-full overflow-hidden rounded-lg border border-ink-0/10 bg-bg-0 sm:aspect-[4/3]">
            <HeatBlockScene progress={progress} />
          </div>
        </div>
      </div>
    </div>
  );
}
