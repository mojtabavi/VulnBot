/** Executor-mode helpers. Docker mode orchestrates the compose lab; remote/local just
 *  rely on the Kali SSH settings written to basic_config.yaml. The pentest itself runs in the
 *  Python pipeline (pentest.py) — runPentest() spawns + streams it. */
import { execa } from 'execa';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import readline from 'node:readline';
import { REPO_ROOT, getDbConfig, getKali } from './config.js';

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
  const r = await docker([...COMPOSE_BASE, '--profile', 'local', '--profile', 'api', '--profile', 'data', 'down']);
  return r.ok ? 'lab down' : `lab down failed: ${r.out}`;
}

// ── MySQL (docker mode): start the compose `mysql` service + create tables ──
/** TCP-probe host:port so a dead MySQL is caught before spawning the pipeline. */
export function dbReachable(host: string, port: number, timeoutMs = 1500): Promise<boolean> {
  return new Promise((resolve) => {
    const sock = new net.Socket();
    const done = (ok: boolean) => { sock.destroy(); resolve(ok); };
    sock.setTimeout(timeoutMs);
    sock.once('connect', () => done(true));
    sock.once('timeout', () => done(false));
    sock.once('error', () => done(false));
    sock.connect(port, host);
  });
}

/** Start the compose `mysql` service (profile: data). Used when MySQL mode = docker. */
export async function mysqlUp(): Promise<string> {
  const r = await docker([...COMPOSE_BASE, '--profile', 'data', 'up', '-d', 'mysql']);
  return r.ok ? 'mysql: container starting' : `mysql up failed: ${r.out}`;
}

/** Wait until MySQL accepts TCP connections (container boot takes a few seconds). */
export async function waitForDb(host: string, port: number, tries = 30): Promise<boolean> {
  for (let i = 0; i < tries; i++) {
    if (await dbReachable(host, port)) return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

/** Create the MySQL tables via the langchain-free `pentest.py --init-db` path. */
export async function initDb(): Promise<{ ok: boolean; out: string }> {
  try {
    const { stdout, stderr } = await execa(pythonExe(), ['pentest.py', '--init-db'], { cwd: REPO_ROOT });
    return { ok: true, out: (stdout || stderr || '').trim() };
  } catch (e: any) {
    return { ok: false, out: (e?.stderr || e?.shortMessage || String(e)).trim() };
  }
}

/** /run preflight: make sure MySQL is reachable before spawning the pipeline.
 *  docker mode auto-starts + inits the compose service; local mode just checks and reports.
 *  Returns ready=true when the pipeline can proceed. `onLine` streams progress to the transcript. */
export async function ensureDb(
  mysqlMode: 'docker' | 'local',
  onLine: (line: string) => void,
): Promise<{ ready: boolean }> {
  const db = getDbConfig();
  const dsn = `${db.host}:${db.port}`;
  let wasDown = false;

  if (!(await dbReachable(db.host, db.port))) {
    if (mysqlMode === 'local') {
      onLine(`MySQL not reachable at ${dsn} — start your local MySQL, then retry /run.`);
      return { ready: false };
    }
    // docker: bring the service up and wait for it to accept connections.
    wasDown = true;
    onLine(`MySQL not reachable at ${dsn} — starting the docker mysql service…`);
    onLine(await mysqlUp());
    if (!(await waitForDb(db.host, db.port))) {
      onLine(`MySQL still not reachable at ${dsn} after starting the container. Check \`docker logs mysql\`.`);
      return { ready: false };
    }
  }

  // Reachable (was up, or just started) — but reachable != schema exists: a running-but-empty MySQL
  // passes the connect check yet has no tables (→ 1146). create_tables() (via --init-db) is idempotent,
  // so always run it here to guarantee the schema. Stay quiet on the common already-up + ok path.
  const init = await initDb();
  if (!init.ok) {
    onLine(`table init failed: ${init.out}`);
    return { ready: false };
  }
  if (wasDown) onLine(init.out || 'MySQL tables ready.');
  return { ready: true };
}

/** /run preflight: make sure the Kali executor is SSH-reachable before spawning the pipeline, so a
 *  dead lab / wrong host surfaces as one clear line instead of a paramiko `getaddrinfo failed`
 *  traceback mid-run. TCP-probes the configured host:port; in docker mode also checks the SSH key
 *  file exists. Returns ready=true when the pipeline can proceed. */
export async function ensureKali(onLine: (line: string) => void): Promise<{ ready: boolean }> {
  const k = getKali();
  if (!k) {
    onLine('Kali not configured — run /setup (or /provider) first.');
    return { ready: false };
  }
  if (k.key_filename) {
    const keyPath = path.isAbsolute(k.key_filename) ? k.key_filename : path.join(REPO_ROOT, k.key_filename);
    if (!fs.existsSync(keyPath)) {
      onLine(`Kali SSH key missing at ${k.key_filename} — generate the lab keypair: \`lab.ps1 up\` (creates docker/agent/keys).`);
      return { ready: false };
    }
  }
  if (!(await dbReachable(k.hostname, k.port))) {
    onLine(`Kali not reachable at ${k.hostname}:${k.port} — is the lab up? run \`lab.ps1 up\` (docker mode) or check your remote Kali.`);
    return { ready: false };
  }
  return { ready: true };
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

// ── real pentest run: spawn the Python pipeline (pentest.py) + stream its output ──
/** Python interpreter to run the pipeline with — prefer the repo venv, else PATH `python`. */
function pythonExe(): string {
  const venv = path.join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'); // Windows venv layout
  return fs.existsSync(venv) ? venv : 'python';
}

export interface PentestRun {
  /** ask the pipeline to stop (SIGINT → the Python side saves + exits). */
  stop: () => void;
}

/** Launch `python pentest.py -m N --no-resume --description <desc> [--agent]` from the repo root
 *  and stream merged stdout/stderr line-by-line. Returns a handle whose stop() kills the process.
 *  `agent` selects the R1 belief-first BeliefAgent loop (default: the legacy 3-phase pipeline).
 *  Real tooling runs on Kali — callers must confirm the target is authorized. */
export function runPentest(
  description: string,
  maxSteps: number,
  onLine: (line: string) => void,
  onExit: (code: number | null) => void,
  agent: boolean = false,
): PentestRun {
  // Run pentest.py directly, NOT `cli.py octopus` — cli.py eagerly imports the FastAPI server +
  // RAG/langchain stack, which isn't needed for a run (enable_rag: false).
  const args = ['pentest.py', '-m', String(maxSteps), '--no-resume', '--description', description];
  if (agent) args.push('--agent');
  const child = execa(
    pythonExe(),
    args,
    { cwd: REPO_ROOT, all: true, buffer: false, env: { PYTHONUNBUFFERED: '1' }, reject: false },
  );
  if (child.all) {
    readline.createInterface({ input: child.all }).on('line', onLine);
  }
  child
    .then((r: any) => onExit(r.exitCode ?? 0))
    .catch((e: any) => {
      if (e?.isCanceled || e?.killed) return onExit(null);
      onLine(`error: ${e?.shortMessage ?? String(e)}`);
      onExit(e?.exitCode ?? 1);
    });
  return { stop: () => child.kill('SIGINT') };
}
