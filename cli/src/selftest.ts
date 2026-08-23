/** Headless self-test (no Ink/TTY): config read/write, /model switch, belief + command handlers. */
import assert from 'node:assert';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'octopus-'));
process.env.PENTEST_ROOT = tmp;
process.env.OCTOPUS_AUTH_FILE = path.join(tmp, 'auth.json'); // keep oauth tests off any real login file

const { writeModelConfig, getModel, setModel } = await import('./config.js');
const { handleCommand } = await import('./commands.js');
const { formatBelief } = await import('./belief.js');

// config write/read + /model switch
writeModelConfig({
  provider: 'openrouter',
  kind: 'openai',
  base_url: 'http://x/v1',
  api_key: 'k',
  model: 'm1',
  auth_mode: 'api_key',
});
assert.strictEqual(getModel(), 'm1', 'writeModelConfig/getModel');
assert.ok(fs.existsSync(path.join(tmp, 'model_config.yaml')), 'model_config.yaml written');
setModel('m2');
assert.strictEqual(getModel(), 'm2', 'setModel');

// new config surface (B3): provider id, auth mode, provider passthrough + /provider switch
const cfgMod = await import('./config.js');
assert.strictEqual(cfgMod.getProviderId(), 'openrouter', 'getProviderId');
assert.strictEqual(cfgMod.getAuthMode(), 'api_key', 'getAuthMode');
assert.ok(cfgMod.listProviders().length >= 6, 'listProviders passthrough');
assert.ok(cfgMod.setProvider('deepseek'), 'setProvider known id');
assert.strictEqual(cfgMod.getProviderId(), 'deepseek', 'setProvider repoints');
assert.ok(!cfgMod.setProvider('nope'), 'setProvider unknown id → false');

// command handlers
const help = await handleCommand('/help');
assert.ok(help.lines.length > 3, '/help');
const model = await handleCommand('/model');
assert.strictEqual(model.action, 'pick-model', '/model (no arg) opens picker');
const switched = await handleCommand('/model m3');
assert.ok(switched.lines[0].includes('m3') && getModel() === 'm3', '/model <name>');
// provider switch + status reflect the registry
const provPick = await handleCommand('/provider');
assert.strictEqual(provPick.action, 'pick-provider', '/provider (no arg) opens picker');
const provSet = await handleCommand('/provider deepseek');
assert.ok(provSet.lines[0].includes('DeepSeek'), '/provider <id> switches');
const provBad = await handleCommand('/provider nope');
assert.ok(provBad.lines[0].includes('unknown provider'), '/provider unknown id');
const status = await handleCommand('/status');
assert.ok(status.lines.some((l) => l.includes('provider:')) && status.lines.some((l) => l.includes('auth:')), '/status shows provider+auth');
const login = await handleCommand('/login');
assert.strictEqual(login.action, 'login', '/login action');
const quit = await handleCommand('/quit');
assert.strictEqual(quit.action, 'quit', '/quit action');
const bel = await handleCommand('/belief');
assert.ok(bel.lines.length > 0, '/belief');
assert.ok(formatBelief().length > 0, 'formatBelief');

// provider registry (B1): unique ids, presets have base_url + /models, generic is escape hatch
const { listProviders, getProvider, modelsUrlFor } = await import('./providers.js');
const provs = listProviders();
assert.ok(provs.length >= 6, 'registry populated');
const ids = new Set(provs.map((p) => p.id));
assert.strictEqual(ids.size, provs.length, 'provider ids unique');
for (const p of provs) {
  assert.ok(p.authModes.length > 0, `${p.id} has an auth mode`);
  if (p.id === 'openai-compatible') {
    assert.strictEqual(p.baseUrl, '', 'custom provider has no preset base_url');
  } else {
    assert.ok(p.baseUrl && modelsUrlFor(p), `${p.id} has base_url + /models URL`);
  }
}
assert.strictEqual(getProvider('openrouter')?.kind, 'openai', 'openrouter reuses OpenAIChat');
assert.strictEqual(getProvider('anthropic')?.kind, 'anthropic', 'native anthropic kind');
assert.ok(getProvider('anthropic')?.authModes.includes('oauth'), 'anthropic offers oauth');
// generic custom base_url derives its /models URL
assert.strictEqual(
  modelsUrlFor(getProvider('openai-compatible')!, 'http://host:8000/v1'),
  'http://host:8000/v1/models',
  'custom /models derived from base_url',
);

// live model fetch (B2): mocked fetch — parse OpenAI/Ollama shapes; errors → [] (never throw)
const { fetchModels } = await import('./models.js');
const okFetch = (async () =>
  ({ ok: true, json: async () => ({ data: [{ id: 'b' }, { id: 'a' }, { id: 'a' }] }) })) as unknown as typeof fetch;
const openaiIds = await fetchModels(getProvider('openrouter')!, { fetchImpl: okFetch });
assert.deepStrictEqual(openaiIds, ['a', 'b'], 'OpenAI shape parsed, deduped + sorted');
const ollamaFetch = (async () =>
  ({ ok: true, json: async () => ({ models: [{ name: 'llama3.1' }] }) })) as unknown as typeof fetch;
assert.deepStrictEqual(
  await fetchModels(getProvider('ollama')!, { fetchImpl: ollamaFetch }),
  ['llama3.1'],
  'Ollama shape parsed',
);
const rejectFetch = (async () => {
  throw new Error('offline');
}) as unknown as typeof fetch;
assert.deepStrictEqual(
  await fetchModels(getProvider('openai')!, { fetchImpl: rejectFetch }),
  [],
  'fetch reject → [] (no throw)',
);
const notOk = (async () => ({ ok: false, json: async () => ({}) })) as unknown as typeof fetch;
assert.deepStrictEqual(
  await fetchModels(getProvider('openai')!, { fetchImpl: notOk }),
  [],
  'HTTP !ok → []',
);
// bare custom base (no models URL) → [] without calling fetch
assert.deepStrictEqual(
  await fetchModels(getProvider('openai-compatible')!),
  [],
  'no models URL → []',
);

// Claude OAuth (B6): PKCE derivation, auth URL params, exchange (mocked), save/load + expiry
const oauth = await import('./oauth.js');
const pk = oauth.makePkce();
assert.ok(pk.verifier.length > 20 && pk.challenge.length > 20 && !/[+/=]/.test(pk.challenge), 'PKCE base64url');
const au = oauth.buildAuthUrl('http://localhost:5/callback');
const auq = new URL(au.url).searchParams;
assert.strictEqual(auq.get('code_challenge_method'), 'S256', 'auth url S256');
assert.ok(auq.get('code_challenge') && auq.get('client_id') && auq.get('state'), 'auth url has pkce+client+state');
assert.strictEqual(auq.get('redirect_uri'), 'http://localhost:5/callback', 'auth url redirect');
const exFetch = (async () =>
  ({ ok: true, json: async () => ({ access_token: 'at', refresh_token: 'rt', expires_in: 3600 }) })) as unknown as typeof fetch;
const tok = await oauth.exchangeCode('code', au.verifier, au.redirectUri, au.state, { fetchImpl: exFetch });
assert.ok(tok.access_token === 'at' && tok.refresh_token === 'rt' && tok.expires_at! > Date.now(), 'exchangeCode maps tokens');
oauth.saveAuth(tok);
assert.deepStrictEqual(oauth.loadAuth()?.access_token, 'at', 'save/load auth roundtrip');
assert.ok(!oauth.isExpired(tok), 'fresh token not expired');
assert.ok(oauth.isExpired({ access_token: 'x', expires_at: Date.now() - 1000 }), 'past-expiry token is expired');
// setAuthToken flips auth_mode to oauth in model_config.yaml
cfgMod.setAuthToken('bearer-xyz');
assert.strictEqual(cfgMod.getAuthMode(), 'oauth', 'setAuthToken flips auth_mode');

fs.rmSync(tmp, { recursive: true, force: true });
console.log('SELFTEST PASS');
