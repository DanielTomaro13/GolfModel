"use client";
import { useMemo, useState } from "react";
import type { CompareRow } from "@/lib/data";
import { price, displayName, MARKET_LABEL } from "@/lib/format";

const MARKETS = ["win", "top_5", "top_10", "top_20", "make_cut"];

export default function CompareTable({ rows }: { rows: CompareRow[] }) {
  const [market, setMarket] = useState("win");
  const [q, setQ] = useState("");

  const books = useMemo(() => {
    const s = new Set<string>();
    rows.filter((r) => r.market === market).forEach((r) => Object.keys(r.books).forEach((b) => s.add(b)));
    return [...s].sort();
  }, [rows, market]);

  const view = useMemo(() => {
    const f = q.trim().toLowerCase();
    return rows
      .filter((r) => r.market === market && (!f || displayName(r.player).toLowerCase().includes(f)))
      .sort((a, b) => b.model_prob - a.model_prob);
  }, [rows, market, q]);

  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "12px 14px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
        {MARKETS.map((m) => (
          <button key={m} onClick={() => setMarket(m)}
            style={{ padding: "5px 11px", borderRadius: 999, fontSize: 13, fontWeight: 600, cursor: "pointer",
              color: market === m ? "#06160d" : "var(--muted)",
              background: market === m ? "var(--accent)" : "transparent",
              border: market === m ? "1px solid var(--accent)" : "1px solid var(--border)" }}>
            {MARKET_LABEL[m]}
          </button>
        ))}
        <input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)}
          style={{ marginLeft: "auto", background: "var(--bg-soft)", border: "1px solid var(--border)", borderRadius: 8, padding: "6px 11px", color: "var(--text)", fontSize: 13 }} />
      </div>
      <div style={{ overflowX: "auto", maxHeight: "74vh" }}>
        <table className="dtable num">
          <thead>
            <tr>
              <th className="left">Player</th>
              <th>Model</th>
              {books.map((b) => <th key={b}>{b}</th>)}
            </tr>
          </thead>
          <tbody>
            {view.map((r) => {
              const best = Math.max(...Object.values(r.books), 0);
              return (
                <tr key={r.pid}>
                  <td className="left">{displayName(r.player)}</td>
                  <td className="gold">{price(r.model_price)}</td>
                  {books.map((b) => {
                    const p = r.books[b];
                    return <td key={b} className={p && p === best ? "good" : "muted"}>{p ? price(p) : "·"}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
