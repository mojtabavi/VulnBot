/** Claude Pro/Max subscription sign-in (OAuth 2.0, PKCE / S256).
 *
 *  ⚠️ GREY AREA: Pro/Max OAuth tokens are issued for Anthropic's first-party clients. Driving a
 *  third-party agent with a subscription token may violate Anthropic's terms, and the endpoints /
 *  client id / beta header are NOT publicly documented — they can change without notice. This is
 *  the USER's own account + own subscription, isolated in this module and fully optional: the
 *  sanctioned API-key path (auth_mode: api_key) works without any of this. Every constant is
 *  overridable via env so it can be re-pinned without a code change.
 *
 *  Flow: build an authorize URL (PKCE, redirect = Anthropic's console callback) → user consents in
 *  the browser → Anthropic shows the auth code → user pastes it back → exchange for
 *  {access_token, refresh_token, expires_in} → persist to a git-ignored cli/.octopus-auth.json
 *  (0600). refresh() renews on expiry. */
import crypto from 'node:crypto';
import fs from 'node:fs';
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
// The public Claude client is registered ONLY for this console callback (loopback is rejected as
// "Invalid request format"). It renders the auth code on-screen for the user to paste back.
const REDIRECT_URI =
  process.env.ANTHROPIC_OAUTH_REDIRECT_URI ?? 'https://console.anthropic.com/oauth/code/callback';

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
/** Build the consent URL + the PKCE/state secrets the exchange step will need.
 *  `code=true` tells the authorize endpoint to render the code for manual paste. */
export function buildAuthUrl(redirectUri = REDIRECT_URI): AuthUrl {
  const { verifier, challenge } = makePkce();
  // Anthropic's Claude OAuth client expects `state` to be the PKCE verifier itself (the callback
  // returns the code as `<code>#<state>` and the token exchange sends both back).
  const state = verifier;
  // Encode manually with encodeURIComponent so scope spaces become %20 (URLSearchParams would
  // use `+`).
  const params: [string, string][] = [
    ['code', 'true'],
    ['client_id', CLIENT_ID],
    ['response_type', 'code'],
    ['redirect_uri', redirectUri],
    ['scope', SCOPES],
    ['code_challenge', challenge],
    ['code_challenge_method', 'S256'],
    ['state', state],
  ];
  const qs = params.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
  return { url: `${AUTHORIZE_URL}?${qs}`, verifier, state, redirectUri };
}

/** Parse what the user pastes after authorizing. Accepts `code#state`, a bare code, or the full
 *  redirect URL (`…?code=…&state=…`). */
export function splitPastedCode(pasted: string): { code: string; state?: string } {
  const t = pasted.trim();
  if (t.includes('code=')) {
    try {
      const u = new URL(t);
      const code = u.searchParams.get('code');
      if (code) return { code, state: u.searchParams.get('state') ?? undefined };
    } catch {
      /* not a URL — fall through */
    }
  }
  const hash = t.indexOf('#');
  if (hash !== -1) return { code: t.slice(0, hash), state: t.slice(hash + 1) };
  return { code: t };
}

/** Exchange a pasted authorization code for tokens and persist them. */
export async function completeLogin(
  pasted: string,
  verifier: string,
  redirectUri: string,
  expectState?: string,
  opts: ExchangeOpts = {},
): Promise<AuthTokens> {
  const { code, state } = splitPastedCode(pasted);
  if (!code) throw new Error('no authorization code pasted');
  if (expectState && state && state !== expectState) throw new Error('state mismatch (possible CSRF)');
  const tokens = await exchangeCode(code, verifier, redirectUri, state ?? expectState, opts);
  saveAuth(tokens);
  return tokens;
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

/** Open a URL in the system browser (best-effort; no dependency).
 *
 *  win32 is fiddly and the OAuth URL is long + full of `&` and `%`:
 *   - `cmd /c start` splits the command line on the first unquoted `&` → truncated URL
 *     (Anthropic: "Missing client_id"). Never use it.
 *   - `explorer.exe <url>` silently no-ops on some machines (observed here).
 *  So on Windows we try, in order, the methods that pass the WHOLE URL to the default handler
 *  without shell `&`-splitting: rundll32 FileProtocolHandler, then PowerShell Start-Process
 *  (URL single-quoted so `&` is literal), then explorer as a last resort. First one that
 *  launches without throwing wins. If all fail, the caller has already printed the full URL. */
export async function openBrowser(url: string): Promise<void> {
  const { execa } = await import('execa');
  const attempts: { file: string; args: string[]; okNonZero?: boolean }[] =
    process.platform === 'win32'
      ? [
          { file: 'rundll32.exe', args: ['url.dll,FileProtocolHandler', url] },
          { file: 'powershell', args: ['-NoProfile', '-NonInteractive', '-Command', `Start-Process '${url.replace(/'/g, "''")}'`] },
          { file: 'explorer.exe', args: [url], okNonZero: true }, // explorer exits non-zero even on success
        ]
      : process.platform === 'darwin'
      ? [{ file: 'open', args: [url] }]
      : [{ file: 'xdg-open', args: [url] }];

  for (const a of attempts) {
    try {
      await execa(a.file, a.args, { detached: true, stdio: 'ignore', windowsHide: true });
      return; // launched
    } catch {
      if (a.okNonZero) return; // explorer likely opened it anyway; stop trying
      // otherwise fall through to the next method
    }
  }
}

/** Begin the manual-paste login: returns the consent URL + the secrets `completeLogin` needs.
 *  The caller opens the URL, the user authorizes, copies the shown code, and passes it to
 *  `completeLogin(pasted, verifier, redirectUri, state)`. */
export function beginLogin(): AuthUrl {
  return buildAuthUrl();
}
