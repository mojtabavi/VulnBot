/** Live-run state derived from the Python pipeline's progress markers.
 *
 *  pentest.py / roles.role emit machine-readable lines (utils/progress.py):
 *      ##OCTO## <kind>|k=v|k=v
 *  parseRunLine folds each streamed stdout line into a RunState the CLI renders as a phase tree
 *  (see ui/RunView.tsx). Non-marker lines become the dim log tail. Pure + clock-injected so the
 *  selftest can exercise it deterministically. */

export const MARKER = '##OCTO##';
const TAIL_MAX = 12;

/** Compress the raw LLM sentinel noise into a short, readable phrase for the transcript.
 *  `**ERROR**: Error code: 429 - {'type':'error','error':{'type':'rate_limit_error'},'request_id':…}`
 *  → `error 429 (rate limited)`. Idempotent; leaves normal lines untouched. The full trace still
 *  lives in logs/Auto-Pentest.log. */
export function cleanErrorText(s: string): string {
  let out = s;
  // `Error code: NNN - { …json… }` (+ any trailing junk on the line) → error NNN (short-type)
  out = out.replace(/Error code:\s*(\d+)\s*-\s*\{.*\}\.?/, (_m, code) => {
    const tag = /rate.?limit/i.test(_m) ? 'rate limited'
      : /overloaded/i.test(_m) ? 'overloaded'
      : /invalid_request/i.test(_m) ? 'invalid request'
      : /authentication|401/i.test(_m) ? 'auth failed'
      : 'API error';
    return `error ${code} (${tag})`;
  });
  // strip the bare sentinel prefix (color already conveys "error")
  out = out.replace(/\*\*ERROR\*\*:\s*/g, '');
  return out;
}

export type RunStepEntry = { seq: string; instr: string; status: 'active' | 'done' };
export type RunTask = { seq: string; instr: string; done: boolean; ok: boolean }; // PTG node for the todo checklist
/** A belief-update event (POMDP posterior) surfaced live for the user — the agent's information-state
 *  over the hidden state S, NOT S itself. `dist` is the updated factor's posterior as hyp→prob. */
export type BeliefUpdate = { step: number; host: string; factor: string; key?: string; action: string; dist: { hyp: string; p: number }[] };
/** Transient LLM-wait state while the client retries a flaky/overloaded API (503/5xx/timeout/429). */
export type LlmWait = { attempt: number; status: string; wait: string };
export type RunPhase = {
  name: string;
  status: 'active' | 'done' | 'failed';
  startedAt: number;
  endedAt?: number;
  tasks?: number; // task COUNT (from the `plan` marker) — kept for the phase header tag
  taskList?: RunTask[]; // the PTG task nodes (from `task` markers) rendered as a live todo checklist
  error?: string;
  steps: RunStepEntry[]; // per-phase react steps in order (last one active while it runs)
};
export type RunStep = { phase: string; seq: string; instr: string } | null;
export type RunState = {
  phases: RunPhase[];
  step: RunStep;
  tail: string[];
  startedAt: number;
  warnings: string[]; // soft failures scraped from the log stream (LLM **ERROR**, empty plan, …)
  logCount: number; // total raw (non-marker) lines seen — the header's "↓ N lines" counter
  error?: string; // set when a phase reports a failure (e.g. planning failed / dead LLM)
  belief?: BeliefUpdate; // latest POMDP belief update (rendered as friendly probability bars)
  decision?: string; // latest policy (π) pick, in plain language ("chose recon — …")
  llmWait?: LlmWait; // set while the LLM API is being retried; drives the ⏳ waiting indicator
};

export function emptyRunState(now: number): RunState {
  return { phases: [], step: null, tail: [], startedAt: now, warnings: [], logCount: 0 };
}

const WARN_MAX = 5;
const STEPS_MAX = 8; // per-phase step history kept for the checklist

/** Close the last still-active step of a phase (on the next step, phase_done, or error). */
function closeActiveStep(steps: RunStepEntry[]): RunStepEntry[] {
  return steps.map((s) => (s.status === 'active' ? { ...s, status: 'done' as const } : s));
}

/** Detect a soft failure inside a raw (non-marker) log line and return a concise warning, else null.
 *  Catches the LLM sentinel `**ERROR**: …` (e.g. a thinking-kwarg reject, a 429) wherever loguru
 *  logs it (summary/plan/react), and an empty `plan: None` — both mean a step silently produced
 *  nothing even if the run limps on. */
export function warningFrom(line: string): string | null {
  const rl = line.indexOf('**RATE-LIMIT**');
  if (rl !== -1) {
    const msg = line.slice(rl + '**RATE-LIMIT**'.length).replace(/^[:\s]+/, '').trim();
    return `rate limit: ${msg || 'reduced thinking'}`;
  }
  const i = line.indexOf('**ERROR**');
  if (i !== -1) {
    const msg = cleanErrorText(line.slice(i + '**ERROR**'.length).replace(/^[:\s]+/, '').trim());
    if (!msg) return 'LLM error: call failed';
    return msg.startsWith('error ') ? `LLM ${msg}` : `LLM error: ${msg}`;
  }
  if (/\bplan:\s*None\b/.test(line)) return 'planner returned no plan (LLM produced no task JSON)';
  return null;
}

export function isMarker(line: string): boolean {
  return line.startsWith(MARKER);
}

/** `##OCTO## step|phase=Scanner|seq=2|instr=nmap ...` → { kind:'step', fields:{...} }.
 *  Values are split on the FIRST `=` so instructions may contain `=` (e.g. --script=vuln). */
function parseMarker(line: string): { kind: string; fields: Record<string, string> } {
  const parts = line.slice(MARKER.length).split('|').map((s) => s.trim()).filter(Boolean);
  const kind = parts.shift() ?? '';
  const fields: Record<string, string> = {};
  for (const tok of parts) {
    const eq = tok.indexOf('=');
    if (eq === -1) continue;
    fields[tok.slice(0, eq)] = tok.slice(eq + 1);
  }
  return { kind, fields };
}

function pushTail(tail: string[], line: string): string[] {
  return [...tail, line].slice(-TAIL_MAX);
}

/** Parse a belief `dist` field (`present:0.72,absent:0.28`) into sorted hyp→prob entries. */
function parseDist(s: string): { hyp: string; p: number }[] {
  const out: { hyp: string; p: number }[] = [];
  for (const tok of (s || '').split(',')) {
    const c = tok.lastIndexOf(':');
    if (c === -1) continue;
    const hyp = tok.slice(0, c).trim();
    const p = Number.parseFloat(tok.slice(c + 1));
    if (hyp && Number.isFinite(p)) out.push({ hyp, p });
  }
  return out.sort((a, b) => b.p - a.p);
}

/** Fold one streamed stdout line into the run state (returns a new state; never mutates). */
export function parseRunLine(state: RunState, line: string, now: number): RunState {
  if (!isMarker(line)) {
    const t = line.trim();
    if (!t) return state;
    const next = { ...state, tail: pushTail(state.tail, t), logCount: state.logCount + 1 };
    const warn = warningFrom(t);
    // surface soft failures prominently; dedupe so a repeated sentinel doesn't spam the panel.
    if (warn && !next.warnings.includes(warn)) {
      next.warnings = [...next.warnings, warn].slice(-WARN_MAX);
    }
    return next;
  }
  const { kind, fields } = parseMarker(line);
  switch (kind) {
    case 'phase': {
      // A new phase begins — close out any still-active phase, then append this one active.
      const phases = state.phases.map((p) =>
        p.status === 'active' ? { ...p, status: 'done' as const, endedAt: p.endedAt ?? now } : p,
      );
      phases.push({ name: fields.name ?? '(phase)', status: 'active', startedAt: now, steps: [] });
      return { ...state, phases, step: null, llmWait: undefined };
    }
    case 'plan': {
      const tasks = Number.parseInt(fields.tasks ?? '', 10);
      const phases = state.phases.map((p) =>
        p.name === fields.phase && p.status === 'active'
          ? { ...p, tasks: Number.isNaN(tasks) ? p.tasks : tasks }
          : p,
      );
      return { ...state, phases, llmWait: undefined };
    }
    case 'task': {
      // Upsert one PTG node by seq into the reporting phase's task list (the live todo checklist).
      // Re-emitted each react step, so status flips (done/ok) and revised instructions land in place.
      const seq = fields.seq ?? '?';
      const node: RunTask = {
        seq,
        instr: fields.instr ?? '',
        done: fields.done === '1',
        ok: fields.ok === '1',
      };
      const phases = state.phases.map((p) => {
        if (p.name !== fields.phase) return p;
        const list = p.taskList ?? [];
        const i = list.findIndex((t) => t.seq === seq);
        const taskList = i === -1 ? [...list, node] : list.map((t, j) => (j === i ? node : t));
        return { ...p, taskList };
      });
      return { ...state, phases, llmWait: undefined };
    }
    case 'belief': {
      // POMDP belief update: the agent's posterior over the hidden state S (its information-state),
      // shown to the user as friendly bars — never S itself. Arrival means the LLM answered → clear wait.
      const belief: BeliefUpdate = {
        step: Number.parseInt(fields.step ?? '0', 10) || 0,
        host: fields.host ?? '?',
        factor: fields.factor ?? '?',
        key: fields.key || undefined,
        action: fields.action ?? '?',
        dist: parseDist(fields.dist ?? ''),
      };
      return { ...state, belief, llmWait: undefined };
    }
    case 'decision': {
      // Policy π pick, rendered in plain language ("why this task").
      const mode = fields.mode ?? '';
      const act = fields.action ?? '';
      const decision =
        mode === 'recon'
          ? `chose recon — resolve uncertainty (info-gain)${act ? ` · ${act}` : ''}`
          : `chose exploit — belief says it pays off${act ? ` · ${act}` : ''}`;
      return { ...state, decision, llmWait: undefined };
    }
    case 'llm': {
      // Transient-API retry indicator: waiting → set it; ok (or any forward marker) → clear it.
      if (fields.state === 'waiting') {
        return {
          ...state,
          llmWait: { attempt: Number.parseInt(fields.attempt ?? '1', 10) || 1, status: fields.status ?? '?', wait: fields.wait ?? '0' },
        };
      }
      return { ...state, llmWait: undefined };
    }
    case 'step': {
      const seq = fields.seq ?? '?';
      const instr = fields.instr ?? '';
      // Append to the reporting phase's step list (closing its previous active step first).
      const phases = state.phases.map((p) =>
        p.name === fields.phase && p.status === 'active'
          ? { ...p, steps: [...closeActiveStep(p.steps), { seq, instr, status: 'active' as const }].slice(-STEPS_MAX) }
          : p,
      );
      return { ...state, phases, step: { phase: fields.phase ?? '', seq, instr }, llmWait: undefined };
    }
    case 'phase_done': {
      // Close the phase — but a phase already marked failed stays failed (error precedes phase_done).
      const phases = state.phases.map((p) =>
        p.name === fields.name && p.status === 'active'
          ? { ...p, status: 'done' as const, endedAt: now, steps: closeActiveStep(p.steps) }
          : p,
      );
      const step = state.step && state.step.phase === fields.name ? null : state.step;
      return { ...state, phases, step, llmWait: undefined };
    }
    case 'error': {
      const msg = fields.msg ?? 'error';
      // Mark the reporting phase failed (red ✗ in the view) and record the run-level reason.
      const phases = state.phases.map((p) =>
        p.name === fields.phase && p.status === 'active'
          ? { ...p, status: 'failed' as const, endedAt: now, error: msg, steps: closeActiveStep(p.steps) }
          : p,
      );
      return { ...state, phases, error: msg, tail: pushTail(state.tail, `⚠ ${msg}`) };
    }
    default:
      return state;
  }
}

/** mm:ss for a millisecond duration. */
export function fmtDuration(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

/** One-line transcript summary shown after the run collapses (exit code from the process). */
export function summarizeRun(state: RunState, code: number | null, now: number): string {
  const done = state.phases.filter((p) => p.status === 'done').length;
  const total = state.phases.length;
  const dur = fmtDuration(now - state.startedAt);
  if (code === null) return `run stopped · ${done}/${total} phases · ${dur}`;
  if (state.error) return `run failed · ${done}/${total} phases · ${dur} · ${cleanErrorText(state.error)}`;
  return `run finished · ${done}/${total} phases · ${dur} · exit ${code}`;
}
