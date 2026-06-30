"use client";
import { useMemo, useState } from "react";
import type { BoardPlayer } from "@/lib/data";
import { pct, displayName, flag } from "@/lib/format";

type Key =
  | "player" | "rating" | "win" | "top_5" | "top_10" | "top_20" | "top_30"
  | "make_cut" | "total_mean";

// label, key, whether lower-is-better (sort asc first), whether it's a probability
const COLS: { key: Key; label: string; lowBetter?: boolean; prob?: boolean }[] = [
  { key: "rating", label: "Rating", lowBetter: true },
  { key: "win", label: "Win", prob: true },
  { key: "top_5", label: "Top 5", prob: true },
  { key: "top_10", label: "Top 10", prob: true },
  { key: "top_20", label: "Top 20", prob: true },
  { key: "top_30", label: "Top 30", prob: true },
  { key: "make_cut", label: "Make Cut", prob: true },
  { key: "total_mean", label: "Proj Total", lowBetter: true },
];

export default function BoardTable({ players }: { players: BoardPlayer[] }) {
  const [sort, setSort] = useState<Key>("win");
  const [dir, setDir] = useState<1 | -1>(-1); // -1 desc, 1 asc
  const [q, setQ] = useState("");

  function clickSort(key: Key) {
    if (key === sort) {
      setDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSort(key);
      const col = COLS.find((c) => c.key === key);
      setDir(key === "player" ? 1 : col?.lowBetter ? 1 : -1);
    }
  }

  const rows = useMemo(() => {
    const f = q.trim().toLowerCase();
    const filtered = f
      ? players.filter((p) => displayName(p.player).toLowerCase().includes(f))
      : players;
    return [...filtered].sort((a, b) => {
      if (sort === "player") return dir * displayName(a.player).localeCompare(displayName(b.player));
      return dir * ((a[sort] as number) - (b[sort] as number));
    });
  }, [players, sort, dir, q]);

  const arrow = (key: Key) => (sort === key ? (dir === 1 ? " ▲" : " ▼") : "");

  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between", padding: "12px 14px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
        <input
          placeholder="Search player…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ background: "var(--bg-soft)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 14, minWidth: 220 }}
        />
        <span className="muted" style={{ fontSize: 13 }}>{rows.length} players · click any column to sort</span>
      </div>
      <div style={{ overflowX: "auto", maxHeight: "78vh" }}>
        <table className="dtable">
          <thead>
            <tr>
              <th className="left">#</th>
              <th className={`left sortable${sort === "player" ? " active" : ""}`} onClick={() => clickSort("player")}>
                Player{arrow("player")}
              </th>
              {COLS.map((c) => (
                <th key={c.key} className={`sortable${sort === c.key ? " active" : ""}`} onClick={() => clickSort(c.key)}>
                  {c.label}{arrow(c.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <tr key={p.pid}>
                <td className="left pos num">{i + 1}</td>
                <td className="left">
                  <span style={{ opacity: 0.85 }}>{flag(p.country)}</span> {displayName(p.player)}
                  {p.amateur ? <span className="chip" style={{ marginLeft: 6, fontSize: 10, padding: "1px 6px" }}>AM</span> : null}
                </td>
                <td className="num muted">{p.rating.toFixed(2)}</td>
                <ProbCell v={p.win} dp={1} gold />
                <ProbCell v={p.top_5} />
                <ProbCell v={p.top_10} />
                <ProbCell v={p.top_20} />
                <ProbCell v={p.top_30} />
                <ProbCell v={p.make_cut} />
                <td className="num muted">{p.total_mean.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProbCell({ v, dp = 0, gold = false }: { v: number; dp?: number; gold?: boolean }) {
  return (
    <td className="num heat" style={{ "--p": v } as React.CSSProperties}>
      <span className={gold ? "gold" : undefined} style={{ fontWeight: gold ? 700 : 400 }}>{pct(v, dp)}</span>
    </td>
  );
}
