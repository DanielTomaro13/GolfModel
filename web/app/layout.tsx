import type { Metadata, Viewport } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { getMeta } from "@/lib/data";
import { timeAgo } from "@/lib/format";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a1410",
};

export const metadata: Metadata = {
  title: { default: "GolfModel — Monte Carlo golf pricing & value", template: "%s — GolfModel" },
  description:
    "A Monte Carlo simulation engine that prices every golf market — winner, top finishes, " +
    "make-cut and Pick'em — from the betting market, and flags value against the bookmakers.",
  applicationName: "GolfModel",
  authors: [{ name: "Daniel Tomaro" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  return (
    <html lang="en">
      <body>
        <header style={{ borderBottom: "1px solid var(--border)", background: "rgba(10,20,16,0.7)", backdropFilter: "blur(8px)", position: "sticky", top: 0, zIndex: 10 }}>
          <div className="container" style={{ padding: "14px 16px", display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <a href="/" style={{ fontWeight: 800, fontSize: 20, letterSpacing: -0.4 }}>
                <span style={{ color: "var(--accent)" }}>⛳ Golf</span>Model
              </a>
              {meta.event && <span className="chip">{meta.event}</span>}
            </div>
            <Nav />
          </div>
        </header>

        <main className="container" style={{ padding: "22px 16px 60px" }}>
          {children}
        </main>

        <footer style={{ borderTop: "1px solid var(--border)", color: "var(--muted)", fontSize: 13 }}>
          <div className="container" style={{ padding: "20px 16px", display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "space-between" }}>
            <span>
              GolfModel · Monte Carlo pricing engine · for research &amp; entertainment only.
            </span>
            <span>
              {meta.generated ? `Model updated ${timeAgo(meta.generated)}` : ""}
              {meta.num_sims ? ` · ${meta.num_sims.toLocaleString()} sims` : ""}
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
