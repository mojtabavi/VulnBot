/*  LogView data layer — read/tail the R4 event log (data/runs/<id>/events.jsonl).
 *
 *  events.jsonl is the on-disk SOURCE OF TRUTH written by the Python agent (utils/events.py):
 *  one JSON record per line, `{ts, run_id, seq, type, ...fields}`. This module is the pure,
 *  unit-tested parse + a live tail (fs.watch with a poll fallback); the rendering lives in
 *  cli/src/ui/LogView.tsx (TL-5.2). The TUI never shows raw JSON — every record is rendered.
 */
import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './config.js';

/** One event record. Extra per-type fields (channel, prior/posterior, z, …) ride along in `[k]`. */
export interface EventRecord {
  ts?: number;
  run_id?: string;
  seq: number;
  type: string;
  [k: string]: unknown;
}

/** Parse ONE JSONL line into a record, or null if blank / malformed / not an event. Pure. */
export function parseEventLine(line: string): EventRecord | null {
  const t = (line ?? '').trim();
  if (!t) return null;
  try {
    const o = JSON.parse(t) as Record<string, unknown>;
    if (o && typeof o.type === 'string' && typeof o.seq === 'number') return o as EventRecord;
  } catch {
    /* torn / non-JSON line — skip */
  }
  return null;
}

/** Parse a whole events.jsonl text blob into records (skips blank/torn lines). Pure. */
export function parseEvents(text: string): EventRecord[] {
  const out: EventRecord[] = [];
  for (const line of (text ?? '').split('\n')) {
    const r = parseEventLine(line);
    if (r) out.push(r);
  }
  return out;
}

/** Keep only records whose `type` is in `types` (null/empty = keep all). Pure. */
export function filterEvents(events: EventRecord[], types?: string[] | null): EventRecord[] {
  if (!types || types.length === 0) return events;
  const set = new Set(types);
  return events.filter((e) => set.has(e.type));
}

// ── per-type summary (pure; the LogView renders these) ──────────────────────────
export const asNum = (v: unknown): number => (typeof v === 'number' ? v : Number.NaN);
export const asStr = (v: unknown): string | undefined => (typeof v === 'string' ? v : undefined);
export const asDist = (v: unknown): Record<string, number> =>
  v && typeof v === 'object' ? (v as Record<string, number>) : {};

/** First non-empty line of a raw tool output, trimmed for a one-line summary. */
export function firstLine(raw: unknown): string {
  const s = asStr(raw) ?? '';
  const line = s.split('\n').find((l) => l.trim()) ?? '';
  return line.length > 60 ? `${line.slice(0, 57)}…` : line;
}

/** A record → one-line summary (icon, color, text) for the LogView. Pure + unit-tested. */
export function summarizeEvent(r: EventRecord): { icon: string; color: string; text: string } {
  switch (r.type) {
    case 'run_start':
      return { icon: '▶', color: 'cyanBright', text: `run start ${asStr(r.session_id) ?? ''}`.trimEnd() };
    case 'run_end':
      return { icon: '■', color: 'cyanBright', text: `run end (steps=${asNum(r.steps) || 0})` };
    case 'action_selected':
      return { icon: '›', color: 'white', text: `chose [${asStr(r.action_type)}] ${asStr(r.action) ?? ''}${r.host ? ` @ ${asStr(r.host)}` : ''}` };
    case 'score': {
      const s = asNum(r.score);
      return { icon: 'ƒ', color: 'gray', text: `R = ${Number.isFinite(s) ? s.toFixed(3) : '—'}` };
    }
    case 'decision':
      return r.kind === 'route'
        ? { icon: '⇄', color: 'blue', text: `route → ${asStr(r.channel) ?? '?'}${r.ok === false ? ' (failed)' : ''}` }
        : { icon: '◆', color: 'blue', text: `decision: ${asStr(r.reason) ?? ''}` };
    case 'observation': {
      const ok = r.success === true ? '✓' : r.success === false ? '✗' : '·';
      return { icon: '📡', color: 'green', text: `${ok} ${asStr(r.channel) ?? '?'} ${asStr(r.tool) ?? ''} — ${firstLine(r.raw)}` };
    }
    case 'belief_update':
      return { icon: '🧠', color: 'magenta', text: `belief ${asStr(r.factor)}${r.key ? `[${asStr(r.key)}]` : ''}${r.host ? ` @ ${asStr(r.host)}` : ''}` };
    case 'llm_likelihoods':
      return { icon: '🔬', color: 'magentaBright', text: `Z ${asStr(r.factor)}${r.key ? `[${asStr(r.key)}]` : ''}` };
    case 'approval_request':
      return { icon: '⚠', color: 'yellow', text: `approval? [${asStr(r.action_type)}] ${asStr(r.action) ?? ''}` };
    case 'approval_result':
      return r.approved
        ? { icon: '✓', color: 'green', text: `approved ${asStr(r.action) ?? ''}` }
        : { icon: '✗', color: 'red', text: `denied ${asStr(r.action) ?? ''}` };
    case 'error':
      return { icon: '✗', color: 'red', text: `error ${asStr(r.where) ?? ''}` };
    default:
      return { icon: '•', color: 'gray', text: r.type };
  }
}

/** Base dir for run logs (mirrors utils/events.py: PENTEST_ROOT/data/runs). */
export function runsDir(): string {
  return path.join(REPO_ROOT, 'data', 'runs');
}

/** events.jsonl path for a run id. */
export function eventsPathFor(runId: string): string {
  return path.join(runsDir(), runId, 'events.jsonl');
}

/** Most-recently-modified run id under data/runs (the "current/last run"), or null if none. */
export function latestRunId(): string | null {
  let best: { id: string; mtime: number } | null = null;
  try {
    for (const name of fs.readdirSync(runsDir())) {
      const p = path.join(runsDir(), name, 'events.jsonl');
      try {
        const m = fs.statSync(p).mtimeMs;
        if (!best || m > best.mtime) best = { id: name, mtime: m };
      } catch {
        /* no events.jsonl in this dir — skip */
      }
    }
  } catch {
    /* no runs dir yet */
  }
  return best?.id ?? null;
}

/** Read + parse all records currently in a run's events.jsonl (empty if missing). */
export function readEvents(runId: string): EventRecord[] {
  try {
    return parseEvents(fs.readFileSync(eventsPathFor(runId), 'utf8'));
  } catch {
    return [];
  }
}

export interface Tail {
  stop: () => void;
}

/** Tail a run's events.jsonl: emit each new record as it is appended. Uses fs.watch when
 *  available and ALWAYS also polls (watch is unreliable across platforms/editors), de-duping by
 *  byte offset so a record is delivered once. Best-effort: file-not-yet-there is fine (it waits). */
export function tailEvents(
  runId: string,
  onRecord: (rec: EventRecord) => void,
  opts: { pollMs?: number } = {},
): Tail {
  const file = eventsPathFor(runId);
  const pollMs = opts.pollMs ?? 400;
  let offset = 0;
  let carry = ''; // partial trailing line between reads
  let stopped = false;

  const drain = (): void => {
    if (stopped) return;
    let size: number;
    try {
      size = fs.statSync(file).size;
    } catch {
      return; // file not there yet
    }
    if (size < offset) {
      // truncated/rotated → restart from the top
      offset = 0;
      carry = '';
    }
    if (size === offset) return;
    let fd: number | null = null;
    try {
      fd = fs.openSync(file, 'r');
      const buf = Buffer.alloc(size - offset);
      fs.readSync(fd, buf, 0, buf.length, offset);
      offset = size;
      carry += buf.toString('utf8');
      let nl: number;
      while ((nl = carry.indexOf('\n')) !== -1) {
        const line = carry.slice(0, nl);
        carry = carry.slice(nl + 1);
        const rec = parseEventLine(line);
        if (rec) onRecord(rec);
      }
    } catch {
      /* transient read error — the next tick retries */
    } finally {
      if (fd !== null) {
        try {
          fs.closeSync(fd);
        } catch {
          /* ignore */
        }
      }
    }
  };

  drain(); // deliver whatever is already there
  const timer = setInterval(drain, pollMs);
  let watcher: fs.FSWatcher | null = null;
  try {
    // Watch the run dir (the file may not exist yet); any change triggers a drain.
    watcher = fs.watch(path.dirname(file), () => drain());
  } catch {
    watcher = null; // watch unsupported → the poll timer carries the load
  }

  return {
    stop: () => {
      stopped = true;
      clearInterval(timer);
      try {
        watcher?.close();
      } catch {
        /* ignore */
      }
    },
  };
}
