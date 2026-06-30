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

const evClass = (ev: number | null | undefined) =>
  ev == null ? "muted" : ev > 0 ? "good" : "bad";
const evTxt = (ev: number | null | undefined) =>
  ev == null ? "—" : `${ev > 0 ? "+" : ""}${(ev * 100).toFixed(1)}%`;

export default function MatchupsView({ extras }: { extras: Extras }) {
  const [tab, setTab] = useState<Tab>("h2h");
  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 8, padding: "12px 14px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
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

      <div style={{ overflowX: "auto", maxHeight: "76vh" }}>
        {tab === "h2h" && <H2H extras={extras} />}
        {tab === "3ball" && <Balls extras={extras} />}
        {tab === "leaders" && <Leaders extras={extras} />}
        {tab === "groups" && <Groups extras={extras} />}
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

function legRow(l: Leg, k: number) {
  return (
    <tr key={k}>
      <td className="left">{displayName(l.player)}</td>
      <td>{(l.model_prob * 100).toFixed(1)}%</td>
      <td className="muted">{l.price ? price(l.price) : "—"}</td>
      <td className={evClass(l.ev)}>{evTxt(l.ev)}</td>
    </tr>
  );
}

function Balls({ extras }: { extras: Extras }) {
  if (!extras.three_balls.length) return <Empty />;
  return (
    <div style={{ padding: 12, display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
      {extras.three_balls.map((t, i) => (
        <div key={i} className="panel" style={{ padding: 0 }}>
          <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--muted)" }}>
            Round {t.round} 3-Ball {t.best_ev != null && t.best_ev > 0 ? <span className="good"> · best +{(t.best_ev * 100).toFixed(0)}%</span> : null}
          </div>
          <table className="dtable num"><tbody>{t.players.map((l, k) => legRow(l, k))}</tbody></table>
        </div>
      ))}
    </div>
  );
}

function Leaders({ extras }: { extras: Extras }) {
  if (!extras.leaders.length) return <Empty />;
  return (
    <div style={{ padding: 12, display: "grid", gap: 14 }}>
      {extras.leaders.map((l, i) => (
        <div key={i} className="panel" style={{ padding: 0 }}>
          <div style={{ padding: "9px 13px", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
            Leader after Round {l.round}
            <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}> · model favourites</span>
          </div>
          <table className="dtable num">
            <thead><tr><th className="left">Player</th><th>Model</th><th>Price</th><th>EV</th></tr></thead>
            <tbody>{l.players.slice(0, 10).map((leg, k) => legRow(leg, k))}</tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function Groups({ extras }: { extras: Extras }) {
  if (!extras.groups.length) return <Empty />;
  return (
    <div style={{ padding: 12, display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
      {extras.groups.map((g, i) => (
        <div key={i} className="panel" style={{ padding: 0 }}>
          <div style={{ padding: "9px 13px", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
            {g.group}
            {g.best_ev != null && g.best_ev > 0 ? <span className="good" style={{ fontSize: 12 }}> · best +{(g.best_ev * 100).toFixed(0)}%</span> : null}
          </div>
          <table className="dtable num">
            <thead><tr><th className="left">Player</th><th>Model</th><th>Price</th><th>EV</th></tr></thead>
            <tbody>{g.players.map((leg, k) => legRow(leg, k))}</tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function Empty() {
  return <div style={{ padding: "26px 18px", color: "var(--muted)", fontSize: 14 }}>No markets live for this event yet.</div>;
}
