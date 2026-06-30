import { getPickem } from "@/lib/data";
import { pct, displayName, MARKET_LABEL } from "@/lib/format";
import { PageHead, Empty } from "@/app/value/page";

export const metadata = { title: "Pick'em" };

export default function PickemPage() {
  const { lines, event } = getPickem();
  const judged = lines.filter((l) => l.ev != null);
  const unmatched = lines.length - judged.length;

  return (
    <>
      <PageHead
        title="Dabble Pick'em"
        sub={`Dabble's PGA Pick'em lines${event ? ` for ${event}` : ""}, each judged against the model. A flat multiplier M is +EV when the model probability × M > 1. Round-strokes lines appear once a round is underway.`}
      />
      {judged.length === 0 ? (
        <Empty msg="No Dabble Pick'em lines are live for this event yet." />
      ) : (
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="dtable num">
              <thead>
                <tr>
                  <th className="left">Player</th>
                  <th className="left">Market</th>
                  <th>Line</th>
                  <th>Multiplier</th>
                  <th>Model %</th>
                  <th>Break-even %</th>
                  <th>EV</th>
                </tr>
              </thead>
              <tbody>
                {judged.map((l, i) => {
                  const be = l.multiplier ? 1 / l.multiplier : null;
                  const ev = l.ev ?? 0;
                  return (
                    <tr key={i}>
                      <td className="left">{displayName(l.player)}</td>
                      <td className="left">
                        {MARKET_LABEL[l.market] || l.market}
                        {l.round ? <span className="muted"> R{l.round}</span> : null}
                      </td>
                      <td className="muted">{l.market === "round_strokes" ? l.line : "—"}</td>
                      <td className="gold">×{l.multiplier?.toFixed(2)}</td>
                      <td>{pct(l.model_prob ?? 0, 1)}</td>
                      <td className="muted">{be != null ? pct(be, 1) : "—"}</td>
                      <td className={ev >= 0 ? "good" : "bad"}>{ev >= 0 ? "+" : ""}{(ev * 100).toFixed(1)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {unmatched > 0 && (
            <div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)", color: "var(--muted)", fontSize: 13 }}>
              {unmatched} line{unmatched === 1 ? "" : "s"} could not be matched to a field player.
            </div>
          )}
        </div>
      )}
    </>
  );
}
