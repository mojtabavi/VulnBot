/** Executor-mode helpers. Docker mode orchestrates the compose lab; remote/local just
 *  rely on the Kali SSH settings written to basic_config.yaml. No pentest logic here. */
import { execa } from 'execa';
import { REPO_ROOT } from './config.js';

// The CLI drives kali via `docker exec`, so labnet stays fully isolated (no published ports).
const COMPOSE_BASE = ['compose'];

async function docker(args: string[]): Promise<{ ok: boolean; out: string }> {
  try {
    const { stdout, stderr } = await execa('docker', args, { cwd: REPO_ROOT });
    return { ok: true, out: (stdout || stderr || '').trim() };
  } catch (e: any) {
    return { ok: false, out: (e?.stderr || e?.shortMessage || String(e)).trim() };
  }
}

export async function dockerAvailable(): Promise<boolean> {
  return (await docker(['info', '--format', '{{.ServerVersion}}'])).ok;
}

export async function labUp(): Promise<string> {
  const r = await docker([...COMPOSE_BASE, '--profile', 'local', 'up', '-d', '--no-deps', 'kali-tools', 'target']);
  return r.ok ? 'lab up: kali-tools + target running' : `lab up failed: ${r.out}`;
}

export async function labDown(): Promise<string> {
  const r = await docker([...COMPOSE_BASE, '--profile', 'local', '--profile', 'api', 'down']);
  return r.ok ? 'lab down' : `lab down failed: ${r.out}`;
}

export async function labStatus(): Promise<string> {
  const r = await docker(['ps', '--format', '{{.Names}} {{.Status}}']);
  if (!r.ok) return `docker not reachable: ${r.out}`;
  const rows = r.out.split('\n').filter((l) => /kali-tools|target|agent|ollama/.test(l));
  return rows.length ? rows.join('\n') : '(no lab containers running)';
}

/** Smoke the executor: run nmap from kali-tools against the target (both in the lab). */
export async function smoke(): Promise<string> {
  const r = await docker(['exec', 'kali-tools', 'nmap', '-Pn', '-T4', 'target']);
  if (!r.ok) return `smoke failed: ${r.out}`;
  const open = r.out.split('\n').filter((l) => /open|Nmap done|scan report/.test(l));
  return `smoke OK (agent->kali->nmap target):\n${open.join('\n')}`;
}
