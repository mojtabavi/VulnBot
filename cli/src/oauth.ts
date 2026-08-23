/** Claude Pro/Max subscription sign-in (OAuth 2.0, PKCE / S256).
 *
 *  ⚠️ GREY AREA: Pro/Max OAuth tokens are issued for Anthropic's first-party clients. Driving a
 *  third-party agent with a subscription token may violate Anthropic's terms, and the endpoints /
 *  client id / beta header are NOT publicly documented — they can change without notice. This is
 *  the USER's own account + own subscription, isolated in this module and fully optional: the
 *  sanctioned API-key path (auth_mode: api_key) works without any of this. Every constant is
 *  overridable via env so it can be re-pinned without a code change.
 *
 *  Flow: build an authorize URL (PKCE) → user consents in the browser → capture the code (loopback
 *  redirect, or paste fallback) → exchange for {access_token, refresh_token, expires_in} → persist
 *  to a git-ignored cli/.octopus-auth.json (0600). refresh() renews on expiry. */
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
// Default cli/.octopus-auth.json; override via env (used by the selftest so it never clobbers a real login).
export const AUTH_FILE = process.env.OCTOPUS_AUTH_FILE ?? path.join(here, '..', '.octopus-auth.json');

// ── endpoints / client (env-overridable; defaults are the known public Claude client) ──
const AUTHORIZE_URL = process.env.ANTHROPIC_OAUTH_AUTHORIZE_URL ?? 'https://claude.ai/oauth/authorize';
const TOKEN_URL = process.env.ANTHROPIC_OAUTH_TOKEN_URL ?? 'https://console.anthropic.com/v1/oauth/token';
const CLIENT_ID = process.env.ANTHROPIC_OAUTH_CLIENT_ID ?? '9d1c250a-e61b-44d9-88ed-5944d1962f5e';
const SCOPES = process.env.ANTHROPIC_OAUTH_SCOPES ?? 'org:create_api_key user:profile user:inference';
const LOOPBACK_PORT = parseInt(process.env.ANTHROPIC_OAUTH_PORT ?? '54545', 10);

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  /** absolute epoch ms when access_token expires */
  expires_at?: number;
  scope?: string;
  token_type?: string;
}

// ── PKCE ─────────────────────────────────────────────────────────────────────
function b64url(buf: Buffer): string {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function makePkce(): { verifier: string; challenge: string } {
  const verifier = b64url(crypto.randomBytes(32));
  const challenge = b64url(crypto.createHash('sha256').update(verifier).digest());
  return { verifier, challenge };
}
export function randomState(): string {
  return b64url(crypto.randomBytes(16));
}

export interface AuthUrl {
  url: string;
  verifier: string;
  state: string;
  redirectUri: string;
}
/** Build the consent URL + the PKCE/state secrets the exchange step will need. */
export function buildAuthUrl(redirectUri = `http://localhost:${LOOPBACK_PORT}/callback`): AuthUrl {
  const { verifier, challenge } = makePkce();
  const state = randomState();
  const q = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: redirectUri,
    scope: SCOPES,
    code_challenge: challenge,
    code_challenge_method: 'S256',
    state,
  });
  return { url: `${AUTHORIZE_URL}?${q.toString()}`, verifier, state, redirectUri };
}

// ── token persistence ─────────────────────────────────────────────────────────
export function saveAuth(t: AuthTokens): void {
  fs.writeFileSync(AUTH_FILE, JSON.stringify(t, null, 2), { encoding: 'utf8', mode: 0o600 });
  try {
    fs.chmodSync(AUTH_FILE, 0o600); // best-effort on POSIX; no-op semantics on Windows
  } catch {
    /* ignore */
  }
}
export function loadAuth(): AuthTokens | null {
  if (!fs.existsSync(AUTH_FILE)) return null;
  try {
    return JSON.parse(fs.readFileSync(AUTH_FILE, 'utf8')) as AuthTokens;
  } catch {
    return null;
  }
}
export function isExpired(t: AuthTokens, skewMs = 60_000): boolean {
  if (!t.expires_at) return false; // unknown expiry → treat as valid, let the API 401 if not
  return Date.now() >= t.expires_at - skewMs;
}

function toTokens(raw: any): AuthTokens {
  return {
    access_token: raw.access_token,
    refresh_token: raw.refresh_token,
    expires_at: raw.expires_in ? Date.now() + raw.expires_in * 1000 : undefined,
    scope: raw.scope,
    token_type: raw.token_type,
  };
}

// ── code → token exchange + refresh ─────────────────────────────────────────────
export interface ExchangeOpts {
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}
async function postToken(body: Record<string, string>, opts: ExchangeOpts = {}): Promise<AuthTokens> {
  const doFetch = opts.fetchImpl ?? globalThis.fetch;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? 15_000);
  try {
    const res = await doFetch(TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error(`token endpoint ${res.status}: ${await res.text().catch(() => '')}`.slice(0, 300));
    return toTokens(await res.json());
  } finally {
    clearTimeout(timer);
  }
}

export async function exchangeCode(
  code: string,
  verifier: string,
  redirectUri: string,
  state?: string,
  opts: ExchangeOpts = {},
): Promise<AuthTokens> {
  const body: Record<string, string> = {
    grant_type: 'authorization_code',
    code,
    client_id: CLIENT_ID,
    redirect_uri: redirectUri,
    code_verifier: verifier,
  };
  if (state) body.state = state;
  return postToken(body, opts);
}

export async function refresh(refreshToken: string, opts: ExchangeOpts = {}): Promise<AuthTokens> {
  const t = await postToken(
    { grant_type: 'refresh_token', refresh_token: refreshToken, client_id: CLIENT_ID },
    opts,
  );
  if (!t.refresh_token) t.refresh_token = refreshToken; // some servers omit it on refresh
  return t;
}

/** Return a valid access token, refreshing + persisting if the stored one is expired. */
export async function getValidToken(opts: ExchangeOpts = {}): Promise<string | null> {
  const t = loadAuth();
  if (!t) return null;
  if (!isExpired(t)) return t.access_token;
  if (!t.refresh_token) return null;
  const next = await refresh(t.refresh_token, opts);
  saveAuth(next);
  return next.access_token;
}

// ── loopback capture: run a one-shot server that catches the redirect ────────────
export function startLoopbackCapture(
  expectState: string,
  port = LOOPBACK_PORT,
  timeoutMs = 300_000,
): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const u = new URL(req.url ?? '/', `http://localhost:${port}`);
      if (u.pathname !== '/callback') {
        res.writeHead(404).end();
        return;
      }
      const code = u.searchParams.get('code');
      const state = u.searchParams.get('state');
      const err = u.searchParams.get('error');
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(
        `<html><body style="font-family:sans-serif"><h3>${
          code && state === expectState ? 'Signed in — you can close this tab.' : 'Sign-in failed.'
        }</h3></body></html>`,
      );
      cleanup();
      if (err) return reject(new Error(`authorization error: ${err}`));
      if (!code) return reject(new Error('no code in callback'));
      if (state !== expectState) return reject(new Error('state mismatch (possible CSRF)'));
      resolve(code);
    });
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error('sign-in timed out'));
    }, timeoutMs);
    function cleanup(): void {
      clearTimeout(timer);
      server.close();
    }
    server.on('error', (e) => {
      cleanup();
      reject(e);
    });
    server.listen(port, '127.0.0.1');
  });
}

/** Open a URL in the system browser (best-effort; no dependency). */
export async function openBrowser(url: string): Promise<void> {
  const { execa } = await import('execa');
  const cmd =
    process.platform === 'win32'
      ? { file: 'cmd', args: ['/c', 'start', '', url] }
      : process.platform === 'darwin'
      ? { file: 'open', args: [url] }
      : { file: 'xdg-open', args: [url] };
  try {
    await execa(cmd.file, cmd.args, { detached: true, stdio: 'ignore' });
  } catch {
    /* user can copy the URL manually */
  }
}

export interface LoginResult {
  tokens: AuthTokens;
}
/** Full loopback login: build URL → (caller shows/opens it) → capture code → exchange → save. */
export async function login(hooks: { onUrl?: (url: string) => void; open?: boolean } = {}): Promise<LoginResult> {
  const { url, verifier, state, redirectUri } = buildAuthUrl();
  hooks.onUrl?.(url);
  if (hooks.open !== false) await openBrowser(url);
  const code = await startLoopbackCapture(state);
  const tokens = await exchangeCode(code, verifier, redirectUri, state);
  saveAuth(tokens);
  return { tokens };
}
