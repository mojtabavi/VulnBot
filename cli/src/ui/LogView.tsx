/*  LogView — human-friendly render of the R4 event log (data/runs/<id>/events.jsonl).
 *
 *  The TUI NEVER shows raw JSON. Each record is rendered per type: belief_update / llm_likelihoods
 *  as probability bars + evidence, observation as a one-line summary with an expandable raw body,
 *  everything else as a compact styled line. Live-tails the file (logview.tailEvents) and supports
 *  ↑/↓ scroll, Enter to expand the selected record, `f` to cycle a type filter, q/Esc to close.
 */
import React, { useEffect, useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { bar, color as probColor } from './BeliefPanel.js';
import { tailEvents, readEvents, summarizeEvent, asDist, type EventRecord } from '../logview.js';

const VIEWPORT = 14; // visible rows

const FILTERS: { label: string; types: string[] | null }[] = [
  { label: 'all', types: null },
  { label: 'belief', types: ['belief_update', 'llm_likelihoods'] },
  { label: 'actions', types: ['action_selected', 'score', 'decision'] },
  { label: 'obs', types: ['observation'] },
  { label: 'hitl', types: ['approval_request', 'approval_result'] },
];

/** Expanded plain-text detail lines for a non-belief record. */
function details(r: EventRecord): string[] {
  const skip = new Set(['ts', 'run_id', 'seq', 'type']);
  const out: string[] = [];
  for (const [k, v] of Object.entries(r)) {
    if (skip.has(k) || v == null) continue;
    let val: string;
    if (typeof v === 'object') val = JSON.stringify(v);
    else val = String(v);
    if (val.length > 120) val = `${val.slice(0, 117)}…`;
    out.push(`${k}: ${val}`);
  }
  return out;
}

/** Probability bars for a distribution, sorted high→low. */
function DistBars({ dist }: { dist: Record<string, number> }): React.ReactElement {
  const rows = Object.entries(dist)
    .map(([hyp, p]) => ({ hyp, p: Number(p) }))
    .filter((e) => Number.isFinite(e.p))
    .sort((a, b) => b.p - a.p);
  return (
    <Box flexDirection="column">
      {rows.map((e) => (
        <Text key={e.hyp} color={probColor(e.p)}>
          {'    '}
          {e.hyp.padEnd(10).slice(0, 10)} {bar(e.p)} {(e.p * 100).toFixed(0).padStart(3)}%
        </Text>
      ))}
    </Box>
  );
}

/** Expanded belief/evidence body: posterior bars, plus prior→posterior + Z for llm_likelihoods. */
function BeliefBody({ r }: { r: EventRecord }): React.ReactElement {
  const posterior = asDist(r.posterior);
  const prior = asDist(r.prior);
  const z = asDist(r.z);
  return (
    <Box flexDirection="column">
      {Object.keys(posterior).length ? (
        <>
          <Text color="gray">    posterior:</Text>
          <DistBars dist={posterior} />
        </>
      ) : null}
      {r.type === 'llm_likelihoods' && Object.keys(z).length ? (
        <Text color="gray">
          {'    '}Z: {Object.entries(z).map(([h, p]) => `${h}=${Number(p).toFixed(2)}`).join('  ')}
        </Text>
      ) : null}
      {r.type === 'llm_likelihoods' && Object.keys(prior).length ? (
        <Text color="gray">
          {'    '}prior: {Object.entries(prior).map(([h, p]) => `${h}=${Number(p).toFixed(2)}`).join('  ')}
        </Text>
      ) : null}
    </Box>
  );
}

export default function LogView({ runId, onClose }: { runId: string; onClose: () => void }): React.ReactElement {
  const [records, setRecords] = useState<EventRecord[]>(() => readEvents(runId));
  const [sel, setSel] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [filterIdx, setFilterIdx] = useState(0);

  useEffect(() => {
    const tail = tailEvents(runId, (rec) => setRecords((rs) => [...rs, rec]));
    return () => tail.stop();
  }, [runId]);

  const filter = FILTERS[filterIdx];
  const view = filter.types ? records.filter((r) => filter.types!.includes(r.type)) : records;
  const selMax = Math.max(0, view.length - 1);
  const clampedSel = Math.min(sel, selMax);

  useInput((ch, key) => {
    if (key.escape || ch === 'q') {
      onClose();
    } else if (key.upArrow || ch === 'k') {
      setSel((s) => Math.max(0, Math.min(s, selMax) - 1));
      setExpanded(false);
    } else if (key.downArrow || ch === 'j') {
      setSel((s) => Math.min(selMax, s + 1));
      setExpanded(false);
    } else if (key.return || ch === ' ') {
      setExpanded((e) => !e);
    } else if (ch === 'f') {
      setFilterIdx((i) => (i + 1) % FILTERS.length);
      setSel(0);
      setExpanded(false);
    } else if (ch === 'g') {
      setSel(0);
    } else if (ch === 'G') {
      setSel(selMax);
    }
  });

  const start = Math.max(0, Math.min(clampedSel - Math.floor(VIEWPORT / 2), Math.max(0, view.length - VIEWPORT)));
  const slice = view.slice(start, start + VIEWPORT);

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1}>
      <Text color="cyanBright" bold wrap="truncate-end">
        event log · {runId}{' '}
        <Text color="gray">
          ({view.length}/{records.length} · filter: {filter.label})
        </Text>
      </Text>
      {view.length === 0 ? <Text color="gray">{'  '}(no events yet…)</Text> : null}
      {slice.map((r, i) => {
        const idx = start + i;
        const active = idx === clampedSel;
        const s = summarizeEvent(r);
        const isBelief = r.type === 'belief_update' || r.type === 'llm_likelihoods';
        return (
          <Box key={`${r.seq}-${idx}`} flexDirection="column">
            <Text color={active ? 'whiteBright' : s.color} inverse={active} wrap="truncate-end">
              {active ? '›' : ' '} {String(r.seq).padStart(3)} {s.icon} {s.text}
            </Text>
            {active && expanded ? (
              isBelief ? (
                <BeliefBody r={r} />
              ) : (
                details(r).map((line, j) => (
                  <Text key={j} color="gray">
                    {'    '}
                    {line}
                  </Text>
                ))
              )
            ) : null}
          </Box>
        );
      })}
      <Text dimColor>↑/↓ move · enter expand · f filter · g/G top/bottom · q close</Text>
    </Box>
  );
}
