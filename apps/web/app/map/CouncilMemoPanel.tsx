"use client";

import type { Memo } from "@coolblock/schema";
import { useCallback, useState } from "react";
import { generateMemo, type MemoProvider } from "../../lib/api";

/**
 * §7.1 L3/L6: the council memo, generated against this plan's own real,
 * computed data, and verified by the numeric provenance guard before
 * it's shown. Every number in the rendered text is underlined -- green
 * with a hover showing the exact payload path it traced back to
 * (`plan.sites[3].cost_usd`), or amber with a warning if L6 could not
 * verify it even after one regeneration attempt. Real cost per click --
 * not cached, and this panel never calls it automatically.
 *
 * Two providers (docs/adr/0019-*.md): Claude (`claude-opus-5`, higher
 * quality, ~15-60s) or Groq (`openai/gpt-oss-120b`, much faster, ~3-8s --
 * added as a fallback for when the Anthropic account's credit balance
 * runs out). Defaults to Groq here since that's the one with a working
 * credit balance as of this build; the backend's own `MEMO_LLM_PROVIDER`
 * env var is the default for any caller that doesn't specify one.
 */
const PROVIDER_LABELS: Record<MemoProvider, string> = {
  groq: "Groq (openai/gpt-oss-120b, fast)",
  anthropic: "Claude (opus, higher quality)",
};

function renderMemoWithHighlights(text: string, numbers: Memo["numbers"]): React.ReactNode[] {
  const sorted = [...numbers].sort((a, b) => a.start - b.start);
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  sorted.forEach((n, i) => {
    if (n.start < cursor) return; // overlapping match (rare) -- keep the earlier one, skip this
    if (n.start > cursor) nodes.push(text.slice(cursor, n.start));
    nodes.push(
      <span
        key={i}
        title={n.verified ? `Source: ${n.path}` : "Could not be verified against the computed data for this plan"}
        style={{
          borderBottom: `2px solid ${n.verified ? "var(--ok)" : "var(--warn)"}`,
          cursor: "help",
        }}
      >
        {text.slice(n.start, n.end)}
      </span>,
    );
    cursor = n.end;
  });
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

export function CouncilMemoPanel({ planId, version }: { planId: string; version: number }) {
  const [provider, setProvider] = useState<MemoProvider>("groq");
  const [includeBaselines, setIncludeBaselines] = useState(false);
  const [memo, setMemo] = useState<Memo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateMemo(planId, version, includeBaselines, provider);
      setMemo(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to generate the memo");
    } finally {
      setLoading(false);
    }
  }, [planId, version, includeBaselines, provider]);

  return (
    <div>
      <SectionLabel>Council memo (§7.1 L3)</SectionLabel>
      <label style={{ display: "flex", flexDirection: "column", gap: 2, fontSize: 11, marginTop: 6 }}>
        <span style={{ opacity: 0.7 }}>Model</span>
        <select
          value={provider}
          disabled={loading}
          onChange={(e) => setProvider(e.target.value as MemoProvider)}
          style={{
            background: "var(--bg-1)",
            color: "var(--paper-0)",
            border: "1px solid var(--bg-2)",
            borderRadius: 4,
            padding: "4px 6px",
            fontSize: 11,
          }}
        >
          {(Object.keys(PROVIDER_LABELS) as MemoProvider[]).map((key) => (
            <option key={key} value={key}>
              {PROVIDER_LABELS[key]}
            </option>
          ))}
        </select>
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, marginTop: 8 }}>
        <input
          type="checkbox"
          checked={includeBaselines}
          disabled={loading}
          onChange={(e) => setIncludeBaselines(e.target.checked)}
        />
        Include baseline comparison (+15-20s)
      </label>
      <button
        onClick={generate}
        disabled={loading}
        style={{
          marginTop: 6,
          background: "none",
          border: "1px solid var(--bg-2)",
          borderRadius: 6,
          color: "var(--paper-0)",
          cursor: loading ? "default" : "pointer",
          padding: "6px 10px",
          fontSize: 11,
        }}
      >
        {loading
          ? `Drafting with ${PROVIDER_LABELS[provider]}...`
          : memo
            ? "Regenerate memo"
            : "Generate council memo"}
      </button>
      {error && <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 6 }}>{error}</p>}
      {memo && (
        <>
          {memo.unverified_count > 0 && (
            <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 8 }}>
              {memo.unverified_count} figure{memo.unverified_count === 1 ? "" : "s"} in this draft could not be
              verified against the computed data for this plan (underlined in amber below).
            </p>
          )}
          <div
            style={{
              marginTop: 8,
              maxHeight: 400,
              overflowY: "auto",
              fontSize: 12,
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              background: "var(--bg-1)",
              border: "1px solid var(--bg-2)",
              borderRadius: 6,
              padding: 10,
            }}
          >
            {renderMemoWithHighlights(memo.text, memo.numbers)}
          </div>
        </>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.5 }}>
      {children}
    </div>
  );
}
