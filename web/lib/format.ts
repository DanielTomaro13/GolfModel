/** Display helpers shared across pages. */

export const pct = (p: number, dp = 1): string =>
  p == null ? "—" : `${(p * 100).toFixed(dp)}%`;

export const price = (decimal: number): string =>
  !decimal || decimal >= 1001 ? "—" : decimal.toFixed(2);

/** Decimal odds -> American, for the punters who prefer it. */
export const american = (d: number): string => {
  if (!d || d <= 1) return "—";
  return d >= 2 ? `+${Math.round((d - 1) * 100)}` : `${Math.round(-100 / (d - 1))}`;
};

export const flag = (countryCode: string): string => {
  // 3-letter country codes mapped to emoji flags.
  const m: Record<string, string> = {
    USA: "🇺🇸", ENG: "🏴", SCO: "🏴", NIR: "🇬🇧", IRL: "🇮🇪", AUS: "🇦🇺",
    RSA: "🇿🇦", ESP: "🇪🇸", JPN: "🇯🇵", KOR: "🇰🇷", CAN: "🇨🇦", SWE: "🇸🇪",
    GER: "🇩🇪", FRA: "🇫🇷", ITA: "🇮🇹", NOR: "🇳🇴", DEN: "🇩🇰", COL: "🇨🇴",
    ARG: "🇦🇷", MEX: "🇲🇽", CHI: "🇨🇱", NZL: "🇳🇿", AUT: "🇦🇹", BEL: "🇧🇪",
    FIN: "🇫🇮", NED: "🇳🇱", CHN: "🇨🇳", TPE: "🇹🇼", THA: "🇹🇭", IND: "🇮🇳",
  };
  return m[countryCode] || "";
};

export const MARKET_LABEL: Record<string, string> = {
  win: "Win", top_5: "Top 5", top_10: "Top 10", top_20: "Top 20",
  top_30: "Top 30", make_cut: "Make Cut", miss_cut: "Miss Cut",
  round_strokes: "Round Strokes",
};

export const timeAgo = (iso: string): string => {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
};

/** Strip "Last, First" -> "First Last" for display. */
export const displayName = (name: string): string => {
  if (name.includes(",")) {
    const [last, first] = name.split(",", 2);
    return `${first.trim()} ${last.trim()}`;
  }
  return name;
};
