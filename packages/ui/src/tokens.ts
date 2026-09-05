/**
 * JS-readable mirror of the colour values in ./tokens.css.
 * Anything that needs a raw hex value at runtime (a MapLibre style spec, a
 * canvas draw call, a deck.gl layer prop) imports from here instead of
 * duplicating the literal -- keep the two files in sync by hand; there are
 * few enough tokens that a build-step generator would be overhead.
 */
export const colorTokens = {
  bg0: "#0a0c0f",
  bg1: "#12151a",
  bg2: "#1a1f26",

  paper0: "#faf8f5",
  paper1: "#ffffff",
  ink0: "#14171c",

  thermal: {
    t00: "#0b0a1f",
    t20: "#3b0f70",
    t40: "#8c2981",
    t60: "#de4968",
    t80: "#fe9f6d",
    t100: "#fcfdbf",
  },

  cool: "#4cc9c0",
  equity: "#f4b860",
  warn: "#e86a5c",
  ok: "#6bcb77",
} as const;
