import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { cleanErrorText, fmtDuration, type RunState } from '../run.js';
import { bar, color as probColor } from './BeliefPanel.js';

const FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

/** Phase name → a Claude-Code-style gerund for the animated header verb. */
function verbFor(phase: string | undefined): string {
  const p = (phase ?? '').toLowerCase();
  if (p.includes('collection')) return 'Reconnoitering';
  if (p.includes('scanner') || p.includes('scan')) return 'Scanning';
  if (p.includes('exploit')) return 'Exploiting';
  return 'Pentesting';
}

/** Claude-Code-style live view of a pentest run: an animated status header (verb · phase x/y · ↓lines),
 *  a phase tree with per-phase elapsed timers + step checklist, ⚠ warnings, and an always-on tail of
 *  the streaming log. Ticks on its own clock so timers advance between lines. Purely presentational —
 *  state comes from parseRunLine (see ../run.ts). */
export default function RunView({
  state,
  paused = false,
  awaiting = null,
}: {
  state: RunState;
  /** R2 HITL: the run is paused (user pressed `p`) — shown until resume. */
  paused?: boolean;
  /** R2 HITL: an action is blocked awaiting approval (its label), or null. */
  awaiting?: { action: string; type?: string } | null;
}): React.ReactElement {
  const [i, setI] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => {
      setI((x) => (x + 1) % FRAMES.length);
      setNow(Date.now());
    }, 120);
    return () => clearInterval(id);
  }, []);
  const spin = FRAMES[i];
  const failed = !!state.error;

  // header bits: current phase (active, else last), phase x/y, verb, elapsed, log-line counter
  const total = state.phases.length;
  const activeIdx = state.phases.findIndex((p) => p.status === 'active');
  const curIdx = activeIdx === -1 ? total - 1 : activeIdx;
  const cur = state.phases[curIdx];
  const verb = verbFor(cur?.name);
  const phaseTag = total ? ` · phase ${curIdx + 1}/${total}${cur ? ` · ${cur.name}` : ''}` : '';
  const meta = `${fmtDuration(now - state.startedAt)}${phaseTag} · ↓ ${state.logCount} lines`;

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={failed ? 'red' : 'cyan'} paddingX={1}>
      <Box>
        <Text color={failed ? 'redBright' : 'cyanBright'} bold wrap="truncate-end">
          {failed ? '✗ pentest run' : `${spin} ${verb}…`} <Text color="gray">({meta})</Text>
        </Text>
      </Box>

      {awaiting ? (
        <Box>
          <Text color="yellowBright" wrap="truncate-end">
            {'  '}⏸ awaiting approval — {awaiting.type ? `[${awaiting.type}] ` : ''}{awaiting.action}
            <Text color="gray"> (a approve · d deny)</Text>
          </Text>
        </Box>
      ) : paused ? (
        <Box>
          <Text color="yellow" wrap="truncate-end">
            {'  '}⏸ paused <Text color="gray">(r to resume · s step · q quit)</Text>
          </Text>
        </Box>
      ) : null}

      {state.llmWait ? (
        // Transient-API retry: the LLM endpoint is flapping (503 overloaded / 5xx / timeout / 429)
        // and the client is backing off. Surface it live so the run reads as waiting, not frozen.
        <Box>
          <Text color="yellow" wrap="truncate-end">
            {'  '}{spin} waiting for LLM response — API {state.llmWait.status}, retry{' '}
            {state.llmWait.attempt}
            {Number(state.llmWait.wait) > 0 ? ` (backing off ${state.llmWait.wait}s)` : ''}…
          </Text>
        </Box>
      ) : null}

      {state.phases.map((p, idx) => {
        const end = p.endedAt ?? now;
        const elapsed = fmtDuration(end - p.startedAt);
        const active = p.status === 'active';
        const isFailed = p.status === 'failed';
        const icon = active ? spin : isFailed ? '✗' : '✓';
        const color = active ? 'yellow' : isFailed ? 'red' : 'green';
        const tasks = p.tasks != null ? `  ${p.tasks} task${p.tasks === 1 ? '' : 's'}` : '';
        return (
          <Box key={idx} flexDirection="column">
            <Box>
              <Text color={color}>  {icon} </Text>
              <Text color={active ? 'white' : isFailed ? 'redBright' : 'gray'}>{p.name}</Text>
              <Text color="gray">   {elapsed}{tasks}</Text>
            </Box>
            {p.taskList && p.taskList.length ? (
              // Live todo checklist: the PTG tasks with status + the current step the agent is on.
              p.taskList.map((t, ti) => {
                const current = active && state.step?.seq === t.seq && !t.done;
                const icon = t.done ? (t.ok ? '✓' : '✗') : current ? (active ? spin : '▶') : '○';
                const color = t.done ? (t.ok ? 'green' : 'red') : current ? 'cyan' : 'gray';
                return (
                  <Box key={ti}>
                    <Text color={color}>      {icon} </Text>
                    <Text color={current ? 'white' : t.done ? 'gray' : 'gray'} wrap="truncate-end">
                      {t.instr || '…'}
                    </Text>
                  </Box>
                );
              })
            ) : (
              p.steps.map((s, si) => {
                const running = s.status === 'active';
                return (
                  <Box key={si}>
                    <Text color={running ? 'cyan' : 'green'}>      {running ? spin : '✓'} </Text>
                    <Text color={running ? 'white' : 'gray'} wrap="truncate-end">
                      step {s.seq}: {s.instr || '…'}
                    </Text>
                  </Box>
                );
              })
            )}
            {isFailed && p.error ? (
              <Text color="red" wrap="truncate-end">      ✗ {p.error}</Text>
            ) : null}
          </Box>
        );
      })}

      {state.belief ? (
        // POMDP belief update, human-friendly: the agent's posterior over the hidden state S (its
        // information-state), NOT S itself. This is exactly what the thesis exists to surface.
        <Box flexDirection="column" marginTop={1}>
          <Text color="magentaBright">
            {'  '}🧠 Belief · step {state.belief.step} · {state.belief.action} on {state.belief.host}
            <Text color="gray"> [{state.belief.factor}{state.belief.key ? `:${state.belief.key}` : ''}]</Text>
          </Text>
          {state.belief.dist.map((d, idx) => (
            <Text key={idx}>
              {'     '}
              <Text color="gray">{d.hyp.padEnd(9)}</Text>
              <Text color={probColor(d.p)}>{bar(d.p)}</Text>
              <Text color="gray"> {d.p.toFixed(2)}</Text>
            </Text>
          ))}
        </Box>
      ) : null}

      {state.decision ? (
        <Box>
          <Text color="cyan" wrap="truncate-end">  ▷ {state.decision}</Text>
        </Box>
      ) : null}

      {state.warnings.length ? (
        <Box flexDirection="column" marginTop={1}>
          {state.warnings.map((w, idx) => (
            <Text key={idx} color="yellow" wrap="truncate-end">  ⚠ {w}</Text>
          ))}
        </Box>
      ) : null}

      {failed ? (
        <Box marginTop={1}>
          <Text color="redBright" bold wrap="truncate-end">  ✗ run aborted: <Text color="red">{state.error}</Text></Text>
        </Box>
      ) : null}

      <Box marginTop={1}>
        {/* The full styled log streams into scrollback (Repl <Static>); here we keep just the last
            line as a live "current activity" ticker so the box stays compact + pinned. */}
        {state.tail.length ? (
          <Text color="gray" dimColor wrap="truncate-end">  {cleanErrorText(state.tail[state.tail.length - 1])}</Text>
        ) : (
          <Text color="gray" dimColor>  … waiting for pipeline output</Text>
        )}
      </Box>
    </Box>
  );
}
