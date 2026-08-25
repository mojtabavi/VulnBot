/*  Loopback control-socket client — the CLI half of the R2 human-in-the-loop back-channel.
 *
 *  The Python agent opens a `ControlServer` on 127.0.0.1:<ephemeral> (utils/control.py) and
 *  announces the port via a `##OCTO## control|port=N` marker on stdout. The Repl (TL-4.2) spots
 *  that marker with `parseControlPort`, then connects a `ControlClient` here.
 *
 *  Frames are newline-delimited JSON, both directions (matching utils/control.py):
 *      agent → CLI : {"event":"approval_request","action":"...","risk":"high"} | {"event":"paused"} | {"event":"resumed"}
 *      CLI → agent : {"cmd":"approve"|"deny"|"pause"|"resume"|"step"|"quit"}
 *
 *  Best-effort by contract: if the agent never opens a server (auto mode), the client simply
 *  never connects and the run proceeds without HITL — a missing socket must never block a run.
 */
import net from 'node:net';

const MARKER = '##OCTO##';

/** Commands the CLI may send to the agent. Mirrors utils/control.py::CONTROL_CMDS. */
export type ControlCmd = 'approve' | 'deny' | 'pause' | 'resume' | 'step' | 'quit';

/** An event frame from the agent. `event` is one of CONTROL_EVENTS; extra fields vary by type. */
export interface ControlEvent {
  event: string;
  [k: string]: unknown;
}

/** Parse the port out of a `##OCTO## control|port=N` marker line, or null if it isn't one.
 *  Mirrors run.ts marker parsing (kind|k=v|k=v, split on the FIRST `=`). */
export function parseControlPort(line: string): number | null {
  if (!line || !line.startsWith(MARKER)) return null;
  const parts = line.slice(MARKER.length).split('|').map((s) => s.trim()).filter(Boolean);
  if (parts.shift() !== 'control') return null;
  for (const tok of parts) {
    const eq = tok.indexOf('=');
    if (eq !== -1 && tok.slice(0, eq) === 'port') {
      const p = Number.parseInt(tok.slice(eq + 1), 10);
      return Number.isInteger(p) && p > 0 ? p : null;
    }
  }
  return null;
}

export interface ControlClientOpts {
  /** called for each well-formed event frame from the agent (approval_request / paused / resumed). */
  onEvent?: (ev: ControlEvent) => void;
  /** called once when the socket closes (agent exited / run ended). */
  onClose?: () => void;
  /** called on a socket error (best-effort; the caller may ignore it). */
  onError?: (err: Error) => void;
  /** called once the TCP connection is established. */
  onConnect?: () => void;
}

/** Newline-JSON client over a loopback TCP socket. One per run (a run has a single front-end). */
export class ControlClient {
  private sock: net.Socket | null = null;
  private buf = '';
  private readonly opts: ControlClientOpts;
  connected = false;

  constructor(opts: ControlClientOpts = {}) {
    this.opts = opts;
  }

  /** Connect to the announced control port. Idempotent-ish: a second call is ignored while open. */
  connect(port: number, host = '127.0.0.1'): void {
    if (this.sock) return;
    const sock = net.createConnection({ port, host });
    this.sock = sock;
    sock.setEncoding('utf8');
    sock.on('connect', () => {
      this.connected = true;
      this.opts.onConnect?.();
    });
    sock.on('data', (chunk: string) => this.onData(chunk));
    sock.on('close', () => {
      this.connected = false;
      this.sock = null;
      this.opts.onClose?.();
    });
    sock.on('error', (e: Error) => {
      this.opts.onError?.(e);
    });
  }

  private onData(chunk: string): void {
    this.buf += chunk;
    let nl: number;
    while ((nl = this.buf.indexOf('\n')) !== -1) {
      const line = this.buf.slice(0, nl);
      this.buf = this.buf.slice(nl + 1);
      const t = line.trim();
      if (!t) continue;
      try {
        const obj = JSON.parse(t) as ControlEvent;
        if (obj && typeof obj.event === 'string') this.opts.onEvent?.(obj);
      } catch {
        /* skip a malformed / torn frame — never throw into the run */
      }
    }
  }

  /** Send one command frame (CLI → agent). Returns false if not connected or the write failed. */
  send(cmd: ControlCmd, extra: Record<string, unknown> = {}): boolean {
    if (!this.sock || !this.connected) return false;
    try {
      this.sock.write(`${JSON.stringify({ cmd, ...extra })}\n`);
      return true;
    } catch {
      return false;
    }
  }

  approve(): boolean { return this.send('approve'); }
  deny(): boolean { return this.send('deny'); }
  pause(): boolean { return this.send('pause'); }
  resume(): boolean { return this.send('resume'); }
  step(): boolean { return this.send('step'); }
  quit(): boolean { return this.send('quit'); }

  close(): void {
    try {
      this.sock?.end();
    } catch {
      /* ignore */
    }
    this.sock = null;
    this.connected = false;
  }
}
