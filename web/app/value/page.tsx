import { getValue, getExtras } from "@/lib/data";
import { pct, price, displayName, MARKET_LABEL } from "@/lib/format";

export const metadata = { title: "Value" };

interface RelRow { player: string; market: string; note: string; model: number; price: number; ev: number; }

function relationalValue(): RelRow[] {
  const e = getExtras();
  const out: RelRow[] = [];
  for (const m of e.matchups) {
    if (m.ev_a != null && m.ev_a > 0 && m.price_a)
      out.push({ player: m.a, market: "H2H", note: `vs ${m.b}`, model: m.model_a, price: m.price_a, ev: m.ev_a });
    if (m.ev_b != null && m.ev_b > 0 && m.price_b)
      out.push({ player: m.b, market: "H2H", note: `vs ${m.a}`, model: m.model_b, price: m.price_b, ev: m.ev_b });
  }
  for (const t of e.three_balls)
    for (const l of t.players)
      if (l.ev != null && l.ev > 0 && l.price)
        out.push({ player: l.player, market: "3-Ball", note: `Round ${t.round}`, model: l.model_prob, price: l.price, ev: l.ev });
  for (const g of e.groups)
    for (const l of g.players)
      if (l.ev != null && l.ev > 0 && l.price)
        out.push({ player: l.player, market: "Group", note: g.group, model: l.model_prob, price: l.price, ev: l.ev });
  return out.sort((a, b) => b.ev - a.ev).slice(0, 25);
}

export default function ValuePage() {
  const { rows, event } = getValue();
  const rel = relationalValue();
  return (
    <>
      <PageHead
        title="Value board"
        sub={`Where the model's fair price beats the bookmaker consensus${event ? ` · ${event}` : ""}. Edge is expected value at the market price; only markets with a real multi-book market are shown.`}
      />

      <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.6, margin: "4px 0 10px" }}>Finish markets</h2>
      {rows.length === 0 ? (
        <Empty msg="No qualifying edges right now — the model agrees with the market, or odds haven't been pulled for this event yet." />
      ) : (
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="dtable num">
              <thead>
                <tr>
                  <th className="left">Player</th><th className="left">Market</th>
                  <th>Model %</th><th>Model fair</th><th>Consensus</th><th>Best price</th><th>Book</th><th>Edge</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td className="left">{displayName(r.player)}</td>
                    <td className="left">{MARKET_LABEL[r.market] || r.market}</td>
                    <td>{pct(r.model_prob, 1)}</td>
                    <td className="muted">{price(r.model_price)}</td>
                    <td className="muted">{price(r.consensus_price)}</td>
                    <td className="gold">{price(r.best_price)}</td>
                    <td className="left muted">{r.best_book}</td>
                    <td className="good">+{(r.edge * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.6, margin: "26px 0 10px" }}>
        Matchups &amp; specials <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>· head-to-heads, 3-balls, groups</span>
      </h2>
      {rel.length === 0 ? (
        <Empty msg="No +EV matchup, 3-ball or group bets right now." />
      ) : (
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="dtable num">
              <thead>
                <tr><th className="left">Player</th><th className="left">Market</th><th className="left">Detail</th><th>Model %</th><th>Price</th><th>EV</th></tr>
              </thead>
              <tbody>
                {rel.map((r, i) => (
                  <tr key={i}>
                    <td className="left">{displayName(r.player)}</td>
                    <td className="left">{r.market}</td>
                    <td className="left muted">{r.note}</td>
                    <td>{pct(r.model, 1)}</td>
                    <td className="gold">{price(r.price)}</td>
                    <td className="good">+{(r.ev * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "9px 14px", borderTop: "1px solid var(--border)", color: "var(--muted)", fontSize: 12 }}>
            EV = model probability × the book&apos;s price − 1. See the Matchups page for every market, not just the edges.
          </div>
        </div>
      )}
    </>
  );
}

export function PageHead({ title, sub }: { title: string; sub: string }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.5, margin: 0 }}>{title}</h1>
      <p className="muted" style={{ margin: "6px 0 0", maxWidth: 720, fontSize: 14, lineHeight: 1.5 }}>{sub}</p>
    </div>
  );
}
export function Empty({ msg }: { msg: string }) {
  return <div className="panel" style={{ padding: "28px 22px", color: "var(--muted)", fontSize: 14 }}>{msg}</div>;
}
