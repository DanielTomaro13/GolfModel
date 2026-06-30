"use client";
import { usePathname } from "next/navigation";
import Link from "next/link";

const TABS = [
  { href: "/", label: "Board" },
  { href: "/value/", label: "Value" },
  { href: "/matchups/", label: "Matchups" },
  { href: "/pickem/", label: "Pick'em" },
  { href: "/compare/", label: "Compare" },
  { href: "/players/", label: "Players" },
  { href: "/about/", label: "About" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {TABS.map((t) => {
        const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            style={{
              padding: "7px 14px", borderRadius: 999, fontSize: 14, fontWeight: 600,
              color: active ? "#06160d" : "var(--muted)",
              background: active ? "var(--accent)" : "transparent",
              border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
            }}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
