import { getBoard, getMeta } from "@/lib/data";
import BoardTable from "@/components/BoardTable";

export default function Home() {
  const board = getBoard();
  const meta = getMeta();
  const src = board.source_win === "book_consensus" ? "bookmaker win market"
    : "model";

  return (
    <>
      <section className="panel" style={{ padding: "20px 22px", marginBottom: 18, display: "flex", flexWrap: "wrap", gap: 18, justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div className="chip" style={{ marginBottom: 8 }}>⛳ {meta.tour?.toUpperCase() || "PGA"} · {board.players.length} players</div>
          <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: -0.6, margin: 0 }}>
            {board.event || "Tournament Board"}
          </h1>
          <p className="muted" style={{ margin: "6px 0 0", maxWidth: 620, fontSize: 14, lineHeight: 1.5 }}>
            Win, top-finish and make-cut probabilities from a Monte Carlo stroke simulation,
            calibrated to the {src}. Every round is drawn around each player&apos;s stroke
            rating; the full board falls out of {meta.num_sims?.toLocaleString() || "20,000"} simulated tournaments.
          </p>
        </div>
        <div style={{ display: "flex", gap: 22, textAlign: "right" }}>
          <Stat label="Field" value={String(board.players.length)} />
          <Stat label="Cut line" value={`Top ${meta.cut_line}`} />
          <Stat label="Sims" value={(meta.num_sims || 20000).toLocaleString()} />
        </div>
      </section>

      <BoardTable players={board.players} />
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent)" }}>{value}</div>
      <div className="muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.6 }}>{label}</div>
    </div>
  );
}
