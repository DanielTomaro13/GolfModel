"use client";
import { useMemo, useState } from "react";
import type { PlayerDetail } from "@/lib/data";
import { pct, displayName, flag } from "@/lib/format";

export default function PlayersTable({ players }: { players: PlayerDetail[] }) {
  const [open, setOpen] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const rows = useMemo(() => {
    const f = q.trim().toLowerCase();
    return f ? players.filter((p) => displayName(p.player).toLowerCase().includes(f)) : players;
  }, [players, q]);

  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
        <input placeholder="Search player…" value={q} onChange={(e) => setQ(e.target.value)}
          style={{ background: "var(--bg-soft)", border: "1px solid var(--border)", borderRadius: 8, padding: "7px 12px", color: "var(--text)", fontSize: 14, minWidth: 220 }} />
      </div>
      <div style={{ overflowX: "auto", maxHeight: "76vh" }}>
        <table className="dtable num">
          <thead>
            <tr>
              <th className="left">Player</th><th>Rating</th><th>Win</th><th>Top 10</th>
              <th>Make Cut</th><th>Proj Total</th><th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <FragmentRow key={p.pid} p={p} open={open === p.pid} onToggle={() => setOpen(open === p.pid ? null : p.pid)} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FragmentRow({ p, open, onToggle }: { p: PlayerDetail; open: boolean; onToggle: () => void }) {
  return (
    <>
      <tr onClick={onToggle} style={{ cursor: "pointer" }}>
        <td className="left">{flag(p.country)} {displayName(p.player)}</td>
        <td className="muted">{p.rating.toFixed(1)}</td>
        <td className="gold">{pct(p.win, 1)}</td>
        <td>{pct(p.top_10, 0)}</td>
        <td>{pct(p.make_cut, 0)}</td>
        <td className="muted">{p.total_mean.toFixed(0)}</td>
        <td className="pos">{open ? "▾" : "▸"}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} style={{ background: "var(--bg-soft)", padding: "14px 18px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 26 }}>
              <div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>ROUND-BY-ROUND (mean ± sd strokes)</div>
                <div style={{ display: "flex", gap: 14 }}>
                  {p.round_mean.map((m, i) => (
                    <div key={i} style={{ textAlign: "center" }}>
                      <div className="muted" style={{ fontSize: 11 }}>R{i + 1}</div>
                      <div style={{ fontWeight: 700 }}>{m.toFixed(1)}</div>
                      <div className="muted" style={{ fontSize: 11 }}>±{p.round_sd[i].toFixed(1)}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>FINISH PROBABILITIES</div>
                <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
                  <span>Top 5 <b className="good">{pct(p.top_5, 0)}</b></span>
                  <span>Top 20 <b className="good">{pct(p.top_20, 0)}</b></span>
                  <span>72-hole total <b>{p.total_mean.toFixed(0)} ± {p.total_sd.toFixed(1)}</b></span>
                </div>
              </div>
              {p.pos_quantiles && Object.keys(p.pos_quantiles).length > 0 && (
                <div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>FINISH POSITION (median / range)</div>
                  <div style={{ fontSize: 13 }}>
                    median <b>{p.pos_quantiles["0.5"]}</b> · 10–90% <b>{p.pos_quantiles["0.1"]}–{p.pos_quantiles["0.9"]}</b>
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
