import { getValue } from "@/lib/data";
import { pct, price, displayName, MARKET_LABEL } from "@/lib/format";

export const metadata = { title: "Value" };

export default function ValuePage() {
  const { rows, event } = getValue();
  return (
    <>
      <PageHead
        title="Value board"
        sub={`Where the model's fair price beats the bookmaker consensus${event ? ` · ${event}` : ""}. Edge is expected value at the consensus price; only markets with a real multi-book market are shown.`}
      />
      {rows.length === 0 ? (
        <Empty msg="No qualifying edges right now — the model agrees with the market, or odds haven't been pulled for this event yet." />
      ) : (
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="dtable num">
              <thead>
                <tr>
                  <th className="left">Player</th>
                  <th className="left">Market</th>
                  <th>Model %</th>
                  <th>Model fair</th>
                  <th>Consensus</th>
                  <th>Best price</th>
                  <th>Book</th>
                  <th>Edge</th>
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
