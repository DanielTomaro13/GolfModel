"use client";
import { useState } from "react";
import type { Extras, Leg } from "@/lib/data";
import { price, displayName } from "@/lib/format";

const TABS = [
  { key: "h2h", label: "Head-to-Head" },
  { key: "3ball", label: "3-Balls" },
  { key: "leaders", label: "Round Leaders" },
  { key: "groups", label: "Groups" },
] as const;
type Tab = (typeof TABS)[number]["key"];

const EXPLAIN: Record<Tab, string> = {
  h2h: "Head-to-head: two players, and you back whichever finishes higher in the tournament (a tie pays the Draw).",
  "3ball": "A 3-ball is three players grouped together — you back whichever one shoots the lowest score that round. Model % is the chance each wins the group; single rounds are noisy, so these are close.",
  leaders: "Who holds the outright lead after the given round (e.g. the first-round leader). Heavy bookmaker margin, so most are negative EV.",
  groups: "Best finisher within a named set of players (e.g. “Top European”) — you back one player to finish ahead of everyone else in that group.",
};

const evClass = (ev: number | null | undefined) => (ev == null ? "muted" : ev > 0 ? "good" : "bad");
const evTxt = (ev: number | null | undefined) => (ev == null ? "—" : `${ev > 0 ? "+" : ""}${(ev * 100).toFixed(1)}%`);

export default function MatchupsView({ extras }: { extras: Extras }) {
  const [tab, setTab] = useState<Tab>("h2h");
  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 8, padding: "12px 14px 0", flexWrap: "wrap" }}>
        {TABS.map((t) => {
          const n = t.key === "h2h" ? extras.matchups.length : t.key === "3ball" ? extras.three_balls.length
            : t.key === "leaders" ? extras.leaders.length : extras.groups.length;
          return (
            <button key={t.key} onClick={() => setTab(t.key)}
              style={{ padding: "6px 13px", borderRadius: 999, fontSize: 13, fontWeight: 600, cursor: "pointer",
                color: tab === t.key ? "#06160d" : "var(--muted)",
                background: tab === t.key ? "var(--accent)" : "transparent",
                border: tab === t.key ? "1px solid var(--accent)" : "1px solid var(--border)" }}>
              {t.label} <span style={{ opacity: 0.7 }}>{n}</span>
            </button>
          );
        })}
      </div>
      <p className="muted" style={{ padding: "10px 16px 12px", margin: 0, fontSize: 13, lineHeight: 1.5, borderBottom: "1px solid var(--border)" }}>
        {EXPLAIN[tab]}
      </p>

      <div style={{ overflowX: "auto", maxHeight: "74vh" }}>
        {tab === "h2h" && <H2H extras={extras} />}
        {tab === "3ball" && <Cards items={extras.three_balls.map((t) => ({ title: `Round ${t.round} 3-Ball`, best: t.best_ev, legs: t.players }))} />}
        {tab === "leaders" && <Cards wide items={extras.leaders.map((l) => ({ title: `Leader after Round ${l.round}`, best: l.best_ev, legs: l.players.slice(0, 10) }))} />}
        {tab === "groups" && <Cards items={extras.groups.map((g) => ({ title: g.group, best: g.best_ev, legs: g.players }))} />}
      </div>
    </div>
  );
}

function H2H({ extras }: { extras: Extras }) {
  if (!extras.matchups.length) return <Empty />;
  return (
    <table className="dtable num">
      <thead><tr>
        <th className="left">Player A</th><th>Model</th><th>Price</th><th>EV</th>
        <th className="left">Player B</th><th>Model</th><th>Price</th><th>EV</th><th>Tie</th>
      </tr></thead>
      <tbody>
        {extras.matchups.map((m, i) => (
          <tr key={i}>
            <td className="left">{m.a}</td>
            <td>{(m.model_a * 100).toFixed(0)}%</td>
            <td className="muted">{m.price_a ? price(m.price_a) : "—"}</td>
            <td className={evClass(m.ev_a)}>{evTxt(m.ev_a)}</td>
            <td className="left">{m.b}</td>
            <td>{(m.model_b * 100).toFixed(0)}%</td>
            <td className="muted">{m.price_b ? price(m.price_b) : "—"}</td>
            <td className={evClass(m.ev_b)}>{evTxt(m.ev_b)}</td>
            <td className="muted">{(m.model_tie * 100).toFixed(0)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Card grid used for 3-balls / leaders / groups. Legs are flex rows so a long
// player name truncates with an ellipsis instead of pushing the numbers out.
function Cards({ items, wide }: { items: { title: string; best: number | null; legs: Leg[] }[]; wide?: boolean }) {
  if (!items.length) return <Empty />;
  const min = wide ? 340 : 300;
  return (
    <div style={{ padding: 12, display: "grid", gap: 12, gridTemplateColumns: `repeat(auto-fill, minmax(${min}px, 1fr))` }}>
      {items.map((it, i) => (
        <div key={i} className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border)", fontSize: 13, display: "flex", justifyContent: "space-between", gap: 8 }}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>{it.title}</span>
            {it.best != null && it.best > 0 ? <span className="good" style={{ whiteSpace: "nowrap" }}>best +{(it.best * 100).toFixed(0)}%</span> : null}
          </div>
          <div style={{ padding: "2px 0" }}>
            {it.legs.map((l, k) => <LegRow key={k} l={l} />)}
          </div>
        </div>
      ))}
    </div>
  );
}

function LegRow({ l }: { l: Leg }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 12px", fontSize: 14 }}>
      <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {displayName(l.player)}
      </span>
      <span className="tabular" style={{ width: 46, textAlign: "right" }}>{(l.model_prob * 100).toFixed(1)}%</span>
      <span className="tabular muted" style={{ width: 42, textAlign: "right" }}>{l.price ? price(l.price) : "—"}</span>
      <span className={`tabular ${evClass(l.ev)}`} style={{ width: 54, textAlign: "right" }}>{evTxt(l.ev)}</span>
    </div>
  );
}

function Empty() {
  return <div style={{ padding: "26px 18px", color: "var(--muted)", fontSize: 14 }}>No markets live for this event yet.</div>;
}
