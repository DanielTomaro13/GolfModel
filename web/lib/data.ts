/**
 * Build-time data loaders. The Python pipeline writes JSON into public/data/
 * before each deploy, so these files are read from disk at build time and the
 * site renders as fully static HTML (great for SEO, no client fetch needed).
 */
import fs from "node:fs";
import path from "node:path";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function read<T>(file: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), "utf8")) as T;
  } catch {
    return fallback;
  }
}

export interface BoardPlayer {
  pid: number; player: string; country: string; amateur: boolean; rating: number;
  win: number; top_5: number; top_10: number; top_20: number; top_30: number;
  make_cut: number; total_mean: number; total_sd: number;
}
export interface CompareRow {
  pid: number; player: string; market: string; model_prob: number;
  model_price: number; books: Record<string, number>;
}
export interface ValueRow {
  pid: number; player: string; market: string; model_prob: number; model_price: number;
  consensus_price: number; best_book: string; best_price: number; edge: number; n_books: number;
}
export interface PickemLine {
  book: string; player: string; market: string; line: number; round: number | null;
  multiplier: number | null; model_prob: number | null; matched: boolean; ev?: number;
}
export interface PlayerDetail {
  pid: number; player: string; country: string; rating: number;
  win: number; top_5: number; top_10: number; top_20: number; make_cut: number;
  round_mean: number[]; round_sd: number[]; total_mean: number; total_sd: number;
  pos_quantiles: Record<string, number>;
}
export interface Meta {
  generated: string; event: string; tour: string; num_sims: number; field_size: number;
  source_win: string; cut_line: number;
  next_event: { name: string; course: string; start_date: string; location: string };
  data_age_days: number | null;
}

export const getBoard = () =>
  read<{ generated: string; event: string; source_win: string; num_sims: number; players: BoardPlayer[] }>(
    "tournament-latest.json", { generated: "", event: "", source_win: "", num_sims: 0, players: [] });

export const getCompare = () =>
  read<{ generated: string; event: string; rows: CompareRow[] }>(
    "compare-latest.json", { generated: "", event: "", rows: [] });

export const getValue = () =>
  read<{ generated: string; event: string; rows: ValueRow[] }>(
    "value-latest.json", { generated: "", event: "", rows: [] });

export const getPickem = () =>
  read<{ generated: string; event: string; lines: PickemLine[] }>(
    "pickem-latest.json", { generated: "", event: "", lines: [] });

export const getPlayers = () =>
  read<{ generated: string; event: string; players: PlayerDetail[] }>(
    "players-latest.json", { generated: "", event: "", players: [] });

export const getMeta = () =>
  read<Meta>("meta-latest.json", {
    generated: "", event: "", tour: "pga", num_sims: 0, field_size: 0, source_win: "",
    cut_line: 65, next_event: { name: "", course: "", start_date: "", location: "" },
    data_age_days: null,
  });
