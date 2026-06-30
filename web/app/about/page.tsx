import { getMeta } from "@/lib/data";
import { PageHead } from "@/app/value/page";
import { timeAgo } from "@/lib/format";

export const metadata = { title: "About" };

export default function AboutPage() {
  const meta = getMeta();
  return (
    <>
      <PageHead
        title="How it works"
        sub="GolfModel is a Monte Carlo stroke-simulation engine that prices a whole golf tournament from a single number per player."
      />
      <div className="panel" style={{ padding: "22px 24px", maxWidth: 760, lineHeight: 1.65, fontSize: 15 }}>
        <Section title="One number per player">
          The engine turns on each player&apos;s <b>rating in strokes per round</b> — lower is better.
          Calibration chooses every rating so the simulated win frequencies reproduce the bookmaker
          win market, with a skill estimate used as the starting point for fast, stable convergence.
        </Section>
        <Section title="Simulating the tournament">
          With ratings fixed, the engine plays the event {meta.num_sims?.toLocaleString() || "20,000"} times.
          Each round is an independent draw around a player&apos;s rating, the field is ranked, the
          halfway cut (top {meta.cut_line}) applied, and ties broken by a random playoff. Every market —
          winner, top 5/10/20, make-cut, round and tournament totals, matchups — is read straight off the
          empirical frequencies of those simulations.
        </Section>
        <Section title="Finding value">
          Model prices are compared to the bookmaker consensus across a dozen-plus books, and to
          Dabble&apos;s PGA Pick&apos;em. Where the model&apos;s fair price beats the market, it surfaces
          on the Value and Pick&apos;em boards.
          <div className="muted" style={{ marginTop: 12, fontSize: 13 }}>
            Model last updated {timeAgo(meta.generated)} · field {meta.field_size} · win market: {meta.source_win.replace("_", " ")}
          </div>
        </Section>
        <p className="muted" style={{ fontSize: 13, marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          For research and entertainment only. Not financial advice. Gamble responsibly — if it stops being
          fun, walk away. 18+.
        </p>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--accent)", margin: "0 0 6px" }}>{title}</h2>
      <p style={{ margin: 0, color: "var(--text)" }}>{children}</p>
    </div>
  );
}
