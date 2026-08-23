/** Pipeline-log formatter: turn a raw streamed stdout line from the Python pentest pipeline into a
 *  classified, styled-ready record so the CLI renders it as an Ink element (not flat text).
 *
 *  The pipeline streams loguru rows:   `TS | LEVEL | module:func:line - message`
 *  plus bare continuation lines (multi-line messages: plan JSON, next_task, <execute> blocks,
 *  summaries). This module is PURE + stateless-per-line so the selftest can exercise it; the React
 *  side (ui/PipelineLine.tsx) only maps a `kind` to colors. Progress markers (##OCTO##) are handled
 *  by run.ts and never reach here. */
import { cleanErrorText } from './run.js';

export interface Loguru {
  ts?: string;
  level?: string;
  where?: string;
  msg: string;
}

/** Split a loguru row into its parts; a non-matching line returns `{ msg: line }` (a bare
 *  continuation line, e.g. a JSON fragment or prose belonging to a multi-line message). */
export function parseLoguru(line: string): Loguru {
  const m = line.match(
    /^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)\s*\|\s*(\w+)\s*\|\s*([\w.]+:[\w<>]+:\d+)\s*-\s*([\s\S]*)$/,
  );
  if (!m) return { msg: line };
  return { ts: m[1], level: m[2], where: m[3], msg: m[4] };
}

export type LogKind =
  | 'command'
  | 'instruction'
  | 'summary'
  | 'plan-json'
  | 'divider'
  | 'error'
  | 'warn'
  | 'info'
  | 'cont'
  | 'debug';

export interface ClassifiedLog {
  kind: LogKind;
  text: string;
  ts?: string; // short HH:mm:ss (for info rows)
  where?: string; // module:func:line (dim, info rows)
}

const EXEC_RE = /<execute>([\s\S]*?)<\/execute>/i;
const RESULT_BANNER_RE = /-{3,}.*Execute Result.*-{3,}/i;

/** Classify one raw pipeline line for styled rendering, or return null to DROP it (blank lines,
 *  DEBUG/TRACE noise). Stateless: a loguru-prefixed line is classified by level + message shape; a
 *  bare line is classified on its own content (an <execute> command is detected directly; a JSON
 *  fragment → plan-json; anything else → a dim continuation). */
export function classifyLog(line: string): ClassifiedLog | null {
  const trimmed = line.replace(/\s+$/, '');
  if (!trimmed.trim()) return null; // drop blank lines

  const lg = parseLoguru(line);
  const msg = lg.msg;

  // executed shell command(s) — the <execute>…</execute> the Generator emits: render as `$ cmd`.
  const ex = msg.match(EXEC_RE);
  if (ex) return { kind: 'command', text: ex[1].trim() };

  // the `----- Execute Result -----` banner pair → one subtle divider.
  if (RESULT_BANNER_RE.test(msg.trim())) return { kind: 'divider', text: 'result' };

  const shortTs = lg.ts ? lg.ts.slice(11) : undefined; // HH:mm:ss(.ms) — drop the date

  if (lg.level) {
    const lvl = lg.level.toUpperCase();
    if (lvl === 'DEBUG' || lvl === 'TRACE') return null; // drop by default (noise)
    if (lvl === 'ERROR' || lvl === 'CRITICAL')
      return { kind: 'error', text: cleanErrorText(msg), ts: shortTs, where: lg.where };
    if (lvl === 'WARNING')
      return { kind: 'warn', text: cleanErrorText(msg), ts: shortTs, where: lg.where };
    // INFO — sub-classify by the message label so instructions/summaries render as distinct blocks.
    if (/^next_task:/i.test(msg))
      return { kind: 'instruction', text: msg.replace(/^next_task:\s*/i, '') || '…', ts: shortTs };
    if (/^summary:/i.test(msg))
      return { kind: 'summary', text: msg.replace(/^summary:\s*/i, '') || '…', ts: shortTs };
    if (/^plan:\s*/i.test(msg))
      return { kind: 'plan-json', text: msg.replace(/^plan:\s*/i, '') || '…', ts: shortTs };
    if (/^LLM Response:/i.test(msg)) return { kind: 'info', text: 'LLM response:', ts: shortTs };
    return { kind: 'info', text: cleanErrorText(msg), ts: shortTs, where: lg.where };
  }

  // no loguru prefix → a continuation line of the previous message.
  const body = trimmed.trim();
  if (/^[[\]{}]/.test(body) || /"(id|instruction|action|dependent_task_ids)"/.test(body))
    return { kind: 'plan-json', text: trimmed };
  return { kind: 'cont', text: trimmed };
}
