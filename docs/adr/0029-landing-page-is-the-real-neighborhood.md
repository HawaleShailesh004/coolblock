# 29. The homepage is the real neighborhood, not a picture of one

Date: 2026-09-16

## Status

Accepted. Replaces the scroll hero from
[`0027-scroll-driven-3d-hero.md`](0027-scroll-driven-3d-hero.md) and the
one-pager in [`0026-marketing-site-real-one-pager.md`](0026-marketing-site-real-one-pager.md).

## Context

The previous homepage had a small grey 3D box floating in ~220vh of empty
scroll, a blurry 540px product screenshot, and text-only sections under
it. Its scroll-progress calculation was also wrong, so the one moment it
was built for — the block heating up — never actually played.

Worse, it was arguing rather than showing. A visitor had to read a claim
about a neighborhood they had never seen.

## Decision

The homepage opens on Edison–Eastlake itself, rendered from the pipeline's
own outputs, and scrolls through the four steps the product takes:

1. **The question** — "Where should the next 40 trees go?"
2. **The heat** — the measured surface temperature as the ground, on the
   same 51–59 °C scale the live app uses.
3. **The choice** — all 773 public tree sites appear at once.
4. **The plan** — the sites the $20,000 plan picks rise in the order the
   optimizer picked them, and the camera moves in.

Everything on the page comes from `scripts/export_landing_scene.py`, which
runs the real solver and writes `heat.png`, `scene.json` and
`baselines.json` into `apps/web/public/landing/`. No number is typed into
the page by hand: re-running the export after the data or the solver
changes updates the copy, the pipeline strip and the comparison chart
together. That is how the switch to the exact solver
(`docs/adr/0028-*.md`) reached the homepage — by re-running one script,
not by editing prose.

Supporting decisions:

- **Type is Overpass**, a descendant of the Highway Gothic lettering on
  American street signs — the voice of public works, for a tool about
  public streets. Figures with a thousands separator use the text face
  with tabular numerals, because Overpass Mono gives the comma a full
  character width and "4 , 057" reads as a typo.
- **The palette is the neighborhood's own materials**: asphalt for the
  story frames, sun-bleached concrete for reading, the thermal ramp only
  where it encodes real temperature, and canopy teal only for what the
  plan picks. Nothing is teal that isn't the plan.
- **The baseline chart** carries its own budget toggle, direct value
  labels, a table view and a plain-language explanation of the narrowest
  and widest leads, computed from the data rather than asserted. Its two
  bar colors were checked with the dataviz validator; the muted grey's
  contrast warning is answered by the labels and the table.
- **Every claim states its limit next to it.** "What it can't tell you"
  sits at the same level as the evidence, not in a footnote: 2 of 3
  validation checks, trees compared only with trees, one neighborhood,
  and what isn't modeled at all.

## Consequences

- three.js loads only on the client, behind a dynamic import, so the
  headline is the page's largest paint. Homepage first-load JS is 115 kB.
- A visitor without WebGL, or with `prefers-reduced-motion`, gets the heat
  image and the same four steps without the camera moves — the story is
  in the text and the image, not only in the animation.
- The page is only as current as the last export run. That is the point:
  when the plan changes, the homepage is wrong until the export is re-run,
  and it says a number that can be checked against the live app.
- The old `HeatBlockScene.tsx`, `ScrollHeatHero.tsx` and `hero-map.png`
  are deleted rather than left beside the new page.
