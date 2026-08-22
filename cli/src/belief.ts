/** Belief-trace viewer: read the Belief Store JSON that the Python agent writes. */
import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './config.js';

function beliefsDir(): string {
  return path.join(REPO_ROOT, 'data', 'beliefs');
}

export function listRuns(): string[] {
  const d = beliefsDir();
  if (!fs.existsSync(d)) return [];
  return fs.readdirSync(d).filter((f) => fs.statSync(path.join(d, f)).isDirectory());
}

export function loadLatest(runId: string): any | null {
  const p = path.join(beliefsDir(), runId, 'latest.json');
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return null;
  }
}

function fmtDist(dist: Record<string, number>): string {
  return Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${k}=${v.toFixed(2)}`)
    .join('  ');
}

/** Format the latest belief of a run (or the newest run) into printable lines. */
export function formatBelief(runId?: string): string[] {
  const runs = listRuns();
  if (runs.length === 0) return ['(no belief traces yet — run an episode first)'];
  const id = runId ?? runs[runs.length - 1];
  const b = loadLatest(id);
  if (!b) return [`(no latest belief for run ${id})`];

  const lines: string[] = [`belief run ${id}  ·  step ${b.step ?? 0}`];
  const hosts = b.hosts ?? {};
  if (Object.keys(hosts).length === 0) lines.push('  (no hosts in belief yet)');
  for (const [host, hb] of Object.entries<any>(hosts)) {
    lines.push(`  host ${host}:`);
    if (hb.os) lines.push(`    os        ${fmtDist(hb.os)}`);
    if (hb.access) lines.push(`    access    ${fmtDist(hb.access)}`);
    for (const [svc, d] of Object.entries<any>(hb.services ?? {})) lines.push(`    svc ${svc}  ${fmtDist(d)}`);
    for (const [v, d] of Object.entries<any>(hb.vulns ?? {})) lines.push(`    vuln ${v}  ${fmtDist(d)}`);
    if (typeof hb.honeypot_likelihood === 'number')
      lines.push(`    honeypot  ${hb.honeypot_likelihood.toFixed(2)}`);
  }
  const lu = b.meta?.last_update;
  if (lu) lines.push(`  last: ${lu.action} on ${lu.host} [${lu.factor}${lu.key ? ':' + lu.key : ''}]`);
  return lines;
}

// ── Structured view for the belief bar panel ─────────────────────────────────
export interface Factor {
  host: string;
  name: string;
  dist: Record<string, number>;
}
export interface BeliefView {
  runId: string | null;
  step: number;
  factors: Factor[];
  last?: string;
}

export function beliefView(runId?: string): BeliefView {
  const runs = listRuns();
  if (runs.length === 0) return { runId: null, step: 0, factors: [] };
  const id = runId ?? runs[runs.length - 1];
  const b = loadLatest(id);
  if (!b) return { runId: id, step: 0, factors: [] };
  const factors: Factor[] = [];
  for (const [host, hb] of Object.entries<any>(b.hosts ?? {})) {
    if (hb.os) factors.push({ host, name: 'os', dist: hb.os });
    if (hb.access) factors.push({ host, name: 'access', dist: hb.access });
    for (const [svc, d] of Object.entries<any>(hb.services ?? {})) factors.push({ host, name: `svc ${svc}`, dist: d });
    for (const [v, d] of Object.entries<any>(hb.vulns ?? {})) factors.push({ host, name: `vuln ${v}`, dist: d });
  }
  const lu = b.meta?.last_update;
  return {
    runId: id,
    step: b.step ?? 0,
    factors,
    last: lu ? `${lu.action} on ${lu.host} [${lu.factor}${lu.key ? ':' + lu.key : ''}]` : undefined,
  };
}
