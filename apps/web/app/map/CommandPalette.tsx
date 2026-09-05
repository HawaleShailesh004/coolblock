"use client";

import { useEffect, useMemo, useState } from "react";

export interface Command {
  id: string;
  label: string;
  run: () => void;
}

/**
 * Command-bar-first (§8.5): opened with Cmd/Ctrl+K. Every entry here is a
 * real action against real state -- no placeholder commands. New commands
 * arrive as later phases give the app something real to do (jump to a
 * site, run a scenario, open the memo).
 */
export function useCommandPalette(commands: Command[]) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const palette = useMemo(
    () => <CommandPaletteDialog open={open} commands={commands} onClose={() => setOpen(false)} />,
    [open, commands],
  );

  return { open, setOpen, palette };
}

function CommandPaletteDialog({
  open,
  commands,
  onClose,
}: {
  open: boolean;
  commands: Command[];
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(10,12,15,0.6)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "15vh",
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-1)",
          color: "var(--paper-0)",
          width: 480,
          maxWidth: "90vw",
          borderRadius: 8,
          boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
          fontFamily: "var(--font-ui)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a command..."
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: "12px 14px",
            background: "transparent",
            border: "none",
            borderBottom: "1px solid var(--bg-2)",
            color: "var(--paper-0)",
            fontSize: 14,
            outline: "none",
          }}
        />
        <div style={{ maxHeight: 280, overflowY: "auto" }}>
          {filtered.length === 0 && (
            <div style={{ padding: "12px 14px", opacity: 0.5, fontSize: 13 }}>No matching commands</div>
          )}
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => {
                c.run();
                onClose();
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "10px 14px",
                background: "transparent",
                border: "none",
                color: "var(--paper-0)",
                fontSize: 13,
                cursor: "pointer",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-2)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
