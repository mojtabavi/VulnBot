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
// switching provider (openrouter → deepseek) must wipe the previous provider's key + model id
assert.strictEqual(cfgMod.getModelConfig().api_key, '', 'setProvider(changed) clears stale key');
assert.strictEqual(cfgMod.getModelConfig().model, '', 'setProvider(changed) clears stale model id');
assert.ok(!cfgMod.setProvider('nope'), 'setProvider unknown id → false');

// db_config write/read + mysqlMode prefs round-trip (MySQL provisioning choice)
cfgMod.writeDbConfig({ host: '10.0.0.5', port: 3307, user: 'u', password: 'p', database: 'd' });
assert.ok(fs.existsSync(path.join(tmp, 'db_config.yaml')), 'db_config.yaml written');
assert.strictEqual(cfgMod.getDbConfig().host, '10.0.0.5', 'writeDbConfig/getDbConfig host');
assert.strictEqual(cfgMod.getDbConfig().port, 3307, 'writeDbConfig/getDbConfig port');
assert.strictEqual(cfgMod.DEFAULT_DB.port, 3306, 'DEFAULT_DB loopback default');
cfgMod.savePrefs({ ...cfgMod.loadPrefs(), setupComplete: true, mysqlMode: 'local' });
assert.strictEqual(cfgMod.loadPrefs().mysqlMode, 'local', 'mysqlMode prefs round-trip');

// command handlers
const help = await handleCommand('/help');
assert.ok(help.lines.length > 3, '/help');
const model = await handleCommand('/model');
assert.strictEqual(model.action, 'pick-model', '/model (no arg) opens picker');
// named providers (deepseek here) reject a hand-typed id — must pick from the live list
const blocked = await handleCommand('/model m3');
assert.ok(getModel() !== 'm3' && blocked.lines.join(' ').includes('live list'), '/model <name> blocked for named provider');
// the custom endpoint DOES accept a hand-typed id
cfgMod.setProvider('openai-compatible');
const switched = await handleCommand('/model custom-1');
assert.ok(switched.lines[0].includes('custom-1') && getModel() === 'custom-1', '/model <name> allowed for custom');
// provider switch + status reflect the registry
const provPick = await handleCommand('/provider');
assert.strictEqual(provPick.action, 'reconfigure-llm', '/provider (no arg) opens guided wizard');
const provSet = await handleCommand('/provider deepseek');
assert.strictEqual(provSet.action, 'reconfigure-llm', '/provider <id> opens guided wizard');
const provBad = await handleCommand('/provider nope');
assert.ok(provBad.lines[0].includes('unknown provider'), '/provider unknown id');
const status = await handleCommand('/status');
assert.ok(status.lines.some((l) => l.includes('provider:')) && status.lines.some((l) => l.includes('auth:')), '/status shows provider+auth');
const login = await handleCommand('/login');
assert.strictEqual(login.action, 'login', '/login action');
// /run builds a description + asks the REPL to spawn the pentest pipeline
const runNoArg = await handleCommand('/run');
assert.ok(!runNoArg.action && runNoArg.lines[0].includes('usage'), '/run (no arg) shows usage');
const runIp = await handleCommand('/run 172.20.0.10');
assert.ok(runIp.action === 'run-pentest' && (runIp.description ?? '').includes('172.20.0.10'), '/run <ip> → run-pentest with description');
const runText = await handleCommand('/run exploit the RCE on host X');
assert.strictEqual(runText.description, 'exploit the RCE on host X', '/run <text> passes description verbatim');
const logNoArg = await handleCommand('/log');
assert.strictEqual(logNoArg.action, 'log', '/log → log action');
assert.strictEqual(logNoArg.runId, undefined, '/log (no arg) → current/last run resolved by the Repl');
const logRun = await handleCommand('/log agent-123');
assert.strictEqual(logRun.runId, 'agent-123', '/log <run> passes the run id');
const quit = await handleCommand('/quit');
assert.strictEqual(quit.action, 'quit', '/quit action');
const bel = await handleCommand('/belief');
assert.ok(bel.lines.length > 0, '/belief');
assert.ok(formatBelief().length > 0, 'formatBelief');

// provider registry (B1): unique ids, presets have base_url + /models, generic is escape hatch
const { listProviders, getProvider, modelsUrlFor, firstLlmStep, stepAfterBaseUrl } = await import('./providers.js');
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

// LLM wizard routing (custom asks Base URL first, then API key → live model fetch; no hand-typed id)
assert.deepStrictEqual(getProvider('openai-compatible')!.authModes, ['api_key'], 'custom = key only');
assert.strictEqual(firstLlmStep(getProvider('openai-compatible')!), 'base_url', 'custom → Base URL first');
assert.strictEqual(stepAfterBaseUrl(getProvider('openai-compatible')!), 'api_key', 'custom: base_url → API key');
assert.strictEqual(firstLlmStep(getProvider('openai')!), 'api_key', 'openai → API key');
assert.strictEqual(firstLlmStep(getProvider('anthropic')!), 'auth', 'anthropic (2 auth modes) → auth pick');
assert.strictEqual(firstLlmStep(getProvider('ollama')!), 'model_fetch', 'ollama (keyless) → model fetch');

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
assert.strictEqual(auq.get('state'), au.verifier, 'auth url state == pkce verifier (Anthropic Claude client)');
assert.strictEqual(auq.get('redirect_uri'), 'http://localhost:5/callback', 'auth url redirect');
assert.strictEqual(auq.get('code'), 'true', 'auth url carries code=true (manual-paste flow)');
// default redirect = Anthropic console callback (public client is registered only for it)
assert.ok(new URL(oauth.buildAuthUrl().url).searchParams.get('redirect_uri')?.includes('console.anthropic.com'), 'default redirect = console callback');
// pasted code parsing: code#state, bare code, and full redirect URL
assert.deepStrictEqual(oauth.splitPastedCode('AAA#BBB'), { code: 'AAA', state: 'BBB' }, 'split code#state');
assert.deepStrictEqual(oauth.splitPastedCode('  JUSTCODE '), { code: 'JUSTCODE' }, 'split bare code (trimmed)');
assert.deepStrictEqual(
  oauth.splitPastedCode('https://console.anthropic.com/oauth/code/callback?code=CC&state=SS'),
  { code: 'CC', state: 'SS' },
  'split full redirect URL',
);
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

// thinking level (Anthropic extended thinking) persists + round-trips
assert.strictEqual(cfgMod.getModelConfig().thinking_level, 'off', 'thinking_level defaults to off');
cfgMod.setThinkingLevel('high');
assert.strictEqual(cfgMod.getModelConfig().thinking_level, 'high', 'setThinkingLevel persists');

// cleanErrorText: compress the raw 429 sentinel blob for the transcript
const { cleanErrorText } = await import('./run.js');
const blob = "**ERROR**: Error code: 429 - {'type': 'error', 'error': {'type': 'rate_limit_error', 'message': 'Error'}, 'request_id': 'req_x'}";
assert.strictEqual(cleanErrorText(blob), 'error 429 (rate limited)', 'cleanErrorText compresses 429 blob');
assert.strictEqual(cleanErrorText(cleanErrorText(blob)), 'error 429 (rate limited)', 'cleanErrorText idempotent');
assert.strictEqual(cleanErrorText('nmap -sV target'), 'nmap -sV target', 'cleanErrorText leaves normal lines');

// run view reducer (Part B): progress markers → phase tree; raw lines → tail; summary
const { emptyRunState, parseRunLine, summarizeRun, isMarker } = await import('./run.js');
let rs = emptyRunState(0);
rs = parseRunLine(rs, '##OCTO## phase|name=Information Collection', 1000);
assert.strictEqual(rs.phases.length === 1 && rs.phases[0].status === 'active', true, 'phase marker opens active phase');
rs = parseRunLine(rs, '##OCTO## plan|phase=Information Collection|tasks=3', 1200);
assert.strictEqual(rs.phases[0].tasks, 3, 'plan marker sets task count');
rs = parseRunLine(rs, '##OCTO## step|phase=Information Collection|seq=0|instr=nmap -sV target', 1300);
assert.ok(rs.step && rs.step.seq === '0' && rs.step.instr.includes('nmap'), 'step marker sets current step');
// task markers → per-phase todo checklist, upserted by seq (re-emit updates status in place)
rs = parseRunLine(rs, '##OCTO## task|phase=Information Collection|seq=1|done=0|ok=0|instr=nmap recon', 1310);
assert.strictEqual(rs.phases[0].taskList?.length, 1, 'task marker creates a todo');
assert.strictEqual(rs.phases[0].taskList![0].done, false, 'new task is pending');
rs = parseRunLine(rs, '##OCTO## task|phase=Information Collection|seq=1|done=1|ok=1|instr=nmap recon', 1320);
assert.strictEqual(rs.phases[0].taskList!.length, 1, 'task marker upserts by seq (length stays 1)');
assert.strictEqual(rs.phases[0].taskList![0].done && rs.phases[0].taskList![0].ok, true, 'upsert flips done + ok');
rs = parseRunLine(rs, '2026-01-01 | INFO | roles.role - some noisy log', 1400);
assert.ok(rs.tail.length === 1 && !isMarker('plain line'), 'raw line goes to tail, not a marker');
rs = parseRunLine(rs, '##OCTO## phase_done|name=Information Collection', 5000);
assert.ok(rs.phases[0].status === 'done' && rs.phases[0].endedAt === 5000 && rs.step === null, 'phase_done closes phase + clears step');
rs = parseRunLine(rs, '##OCTO## phase|name=Vulnerability Scanner', 5100);
assert.ok(rs.phases.length === 2 && rs.phases[0].status === 'done', 'new phase auto-closes any still-active phase');
const summary = summarizeRun(rs, 0, 65000);
assert.ok(summary.includes('finished') && summary.includes('exit 0') && summary.includes('01:05'), 'summarizeRun formats phases/duration/exit');
// error marker → phase goes failed (not done-green), run-level error set, summary says "failed"
let ef = emptyRunState(0);
ef = parseRunLine(ef, '##OCTO## phase|name=Information Collection', 100);
ef = parseRunLine(ef, '##OCTO## error|phase=Information Collection|msg=planning failed (no plan created)', 200);
ef = parseRunLine(ef, '##OCTO## phase_done|name=Information Collection', 300);
assert.ok(ef.phases[0].status === 'failed' && ef.phases[0].error?.includes('planning failed'), 'error marker marks phase failed + keeps reason through phase_done');
assert.ok(ef.error?.includes('planning failed'), 'error marker sets run-level error');
const failSummary = summarizeRun(ef, 0, 5000);
assert.ok(failSummary.startsWith('run failed') && failSummary.includes('planning failed'), 'summarizeRun surfaces failure even on exit 0');
// per-phase step history: each step marker closes the previous + opens the new; phase_done closes last
let sh = emptyRunState(0);
sh = parseRunLine(sh, '##OCTO## phase|name=Scanning', 10);
sh = parseRunLine(sh, '##OCTO## step|phase=Scanning|seq=0|instr=nikto -host target', 20);
sh = parseRunLine(sh, '##OCTO## step|phase=Scanning|seq=1|instr=sqlmap -u target', 30);
assert.ok(sh.phases[0].steps.length === 2, 'step markers accumulate per-phase history');
assert.strictEqual(sh.phases[0].steps[0].status, 'done', 'previous step closed when next opens');
assert.strictEqual(sh.phases[0].steps[1].status, 'active', 'latest step is active');
sh = parseRunLine(sh, '##OCTO## phase_done|name=Scanning', 40);
assert.ok(sh.phases[0].steps.every((s) => s.status === 'done'), 'phase_done closes the last active step');
// soft failures scraped from raw loguru lines → yellow warnings (deduped), not just the dim tail
const { warningFrom } = await import('./run.js');
assert.ok(warningFrom("...get_summary:37 - summary: **ERROR**: Messages.create() got an unexpected keyword argument 'thinking'")?.startsWith('LLM error:'), 'warningFrom extracts **ERROR** sentinel');
assert.strictEqual(warningFrom('...planner:plan:30 - plan: None'), 'planner returned no plan (LLM produced no task JSON)', 'warningFrom flags empty plan');
assert.strictEqual(warningFrom('...belief initialized for run 945c'), null, 'warningFrom ignores normal INFO lines');
assert.ok(warningFrom('**RATE-LIMIT**: reduced thinking high->medium to avoid rate limiting')?.startsWith('rate limit:'), 'warningFrom maps **RATE-LIMIT** notice');
// logCount tracks raw (non-marker) lines for the header counter; markers don't count
let lc = emptyRunState(0);
lc = parseRunLine(lc, '##OCTO## phase|name=X', 1);
lc = parseRunLine(lc, 'some raw log line', 2);
lc = parseRunLine(lc, 'another raw log line', 3);
assert.strictEqual(lc.logCount, 2, 'logCount counts raw lines only (not markers)');
let wr = emptyRunState(0);
wr = parseRunLine(wr, '2026-08-23 | INFO | actions.plan_summary:get_summary:37 - summary: **ERROR**: boom', 10);
wr = parseRunLine(wr, '2026-08-23 | INFO | actions.plan_summary:get_summary:37 - summary: **ERROR**: boom', 20); // dup
wr = parseRunLine(wr, '2026-08-23 | INFO | actions.planner:plan:30 - plan: None', 30);
assert.strictEqual(wr.warnings.length, 2, 'warnings dedupe repeats + collect distinct soft failures');

// belief/decision/llm markers → live POMDP panels; llmWait set on waiting, cleared on ok/progress
let bs = emptyRunState(0);
bs = parseRunLine(bs, '##OCTO## phase|name=Collector', 1);
bs = parseRunLine(bs, '##OCTO## llm|state=waiting|attempt=2|status=503|wait=4', 2);
assert.ok(bs.llmWait && bs.llmWait.attempt === 2 && bs.llmWait.status === '503', 'llm waiting sets llmWait');
bs = parseRunLine(bs, '##OCTO## llm|state=ok', 3);
assert.strictEqual(bs.llmWait, undefined, 'llm ok clears llmWait');
bs = parseRunLine(bs, '##OCTO## llm|state=waiting|attempt=1|status=529|wait=2', 4);
assert.ok(bs.llmWait, 'llmWait re-armed');
bs = parseRunLine(bs, '##OCTO## step|phase=Collector|seq=0|instr=nmap', 5);
assert.strictEqual(bs.llmWait, undefined, 'forward progress (step) clears llmWait');
bs = parseRunLine(bs, '##OCTO## belief|phase=Collector|step=3|host=target|factor=vulns|key=cve-x|action=exploit:x|dist=present:0.72,absent:0.28', 6);
assert.ok(bs.belief && bs.belief.step === 3 && bs.belief.host === 'target', 'belief marker sets belief');
assert.strictEqual(bs.belief!.dist.length, 2, 'belief dist parsed into 2 entries');
assert.ok(bs.belief!.dist[0].hyp === 'present' && Math.abs(bs.belief!.dist[0].p - 0.72) < 1e-9, 'belief dist sorted, prob parsed');
bs = parseRunLine(bs, '##OCTO## decision|phase=Collector|mode=recon|action=recon:probe', 7);
assert.ok(bs.decision?.startsWith('chose recon'), 'decision marker → plain-language recon');

// logfmt: loguru parse + classify
const { parseLoguru, classifyLog } = await import('./logfmt.js');
const lg = parseLoguru('2026-08-23 22:18:42.017 | INFO     | actions.execute_task:shell_operation:71 - Running [x]');
assert.ok(lg.level === 'INFO' && lg.where === 'actions.execute_task:shell_operation:71' && lg.msg.startsWith('Running'), 'parseLoguru splits a real row');
assert.strictEqual(parseLoguru('bare continuation line').level, undefined, 'parseLoguru: bare line → no level');
const cmd = classifyLog('2026-08-23 22:18:42 | INFO | actions.write_code:run:21 - <execute>nmap -sV target</execute>');
assert.ok(cmd && cmd.kind === 'command' && cmd.text === 'nmap -sV target', 'classifyLog: <execute> → command');
assert.strictEqual(classifyLog('    just some prose continuation')!.kind, 'cont', 'classifyLog: bare prose → cont');
assert.strictEqual(classifyLog(''), null, 'classifyLog: blank → dropped');
assert.strictEqual(classifyLog('2026-08-23 22:18:42 | DEBUG | x:y:1 - noisy'), null, 'classifyLog: DEBUG → dropped');
assert.strictEqual(classifyLog('2026-08-23 22:18:42 | INFO | actions.write_code:run:19 - next_task: recon the host')!.kind, 'instruction', 'classifyLog: next_task → instruction');
assert.strictEqual(classifyLog('2026-08-23 22:18:42 | ERROR | x:y:1 - boom')!.kind, 'error', 'classifyLog: ERROR → error');

// control socket (R2 TL-4.1): marker port parse + newline-JSON frame round-trip over loopback
const { parseControlPort, ControlClient } = await import('./control.js');
assert.strictEqual(parseControlPort('##OCTO## control|port=54321'), 54321, 'parseControlPort reads the port');
assert.strictEqual(parseControlPort('##OCTO## event|type=run_start|seq=1'), null, 'parseControlPort ignores non-control markers');
assert.strictEqual(parseControlPort('plain log line'), null, 'parseControlPort ignores non-markers');

await (async () => {
  const net = await import('node:net');
  const received: unknown[] = [];
  const evParts: string[] = [];
  const server = net.createServer((sock) => {
    sock.setEncoding('utf8');
    let buf = '';
    sock.on('data', (c: string) => {
      buf += c;
      let nl: number;
      while ((nl = buf.indexOf('\n')) !== -1) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (line.trim()) received.push(JSON.parse(line));
      }
    });
    // agent → CLI: send an approval_request frame
    sock.write(JSON.stringify({ event: 'approval_request', action: 'exploit vsftpd', risk: 'high' }) + '\n');
  });
  await new Promise<void>((res) => server.listen(0, '127.0.0.1', () => res()));
  const port = (server.address() as import('node:net').AddressInfo).port;

  await new Promise<void>((resolve, reject) => {
    const client: InstanceType<typeof ControlClient> = new ControlClient({
      onConnect: () => { client.approve(); client.send('step'); },
      onEvent: (ev) => { evParts.push(ev.event); },
      onError: reject,
    });
    client.connect(port);
    setTimeout(() => { client.close(); server.close(); resolve(); }, 150);
  });

  assert.deepStrictEqual(evParts, ['approval_request'], 'client received the agent event frame');
  assert.strictEqual((received[0] as { cmd: string }).cmd, 'approve', 'agent got the approve command frame');
  assert.strictEqual((received[1] as { cmd: string }).cmd, 'step', 'agent got the step command frame');
})();

// logview (R4 TL-5.1): pure parse + filter of the event log, and tail delivers appended records
const lv = await import('./logview.js');
assert.strictEqual(lv.parseEventLine('  '), null, 'parseEventLine: blank → null');
assert.strictEqual(lv.parseEventLine('not json'), null, 'parseEventLine: garbage → null');
assert.strictEqual(lv.parseEventLine('{"foo":1}'), null, 'parseEventLine: missing type/seq → null');
const rec0 = lv.parseEventLine('{"type":"observation","seq":3,"raw":"80 open"}');
assert.ok(rec0 && rec0.type === 'observation' && rec0.seq === 3, 'parseEventLine: valid record');
const evs = lv.parseEvents('{"type":"run_start","seq":1}\n\nbad line\n{"type":"observation","seq":2}\n');
assert.strictEqual(evs.length, 2, 'parseEvents: skips blank + torn lines');
assert.deepStrictEqual(lv.filterEvents(evs, ['observation']).map((e) => e.seq), [2], 'filterEvents by type');
assert.strictEqual(lv.filterEvents(evs, []).length, 2, 'filterEvents empty types = keep all');

await (async () => {
  // tail: PENTEST_ROOT is `tmp`, so runsDir() = tmp/data/runs
  const runId = 'lvrun';
  const dir = path.join(tmp, 'data', 'runs', runId);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, 'events.jsonl');
  fs.writeFileSync(file, '{"type":"run_start","seq":1}\n'); // pre-existing record
  const got: number[] = [];
  const tail = lv.tailEvents(runId, (r) => got.push(r.seq), { pollMs: 30 });
  await new Promise((r) => setTimeout(r, 60));
  fs.appendFileSync(file, '{"type":"observation","seq":2}\n'); // appended after tail starts
  await new Promise((r) => setTimeout(r, 120));
  tail.stop();
  assert.deepStrictEqual(got, [1, 2], 'tailEvents delivers existing + appended records once');
  assert.strictEqual(lv.latestRunId(), runId, 'latestRunId finds the run');
  assert.deepStrictEqual(lv.readEvents(runId).map((e) => e.seq), [1, 2], 'readEvents reads the whole file');
})();

// logview per-type summary (R4 TL-5.4): each record type renders a distinct human-friendly line
{
  const S = lv.summarizeEvent;
  assert.strictEqual(S({ type: 'observation', seq: 1, channel: 'ssh', tool: 'nmap', success: true, raw: '80/tcp open\n443 open' }).text,
    '✓ ssh nmap — 80/tcp open', 'summarize observation: ok + channel + first raw line');
  assert.strictEqual(S({ type: 'decision', seq: 2, kind: 'route', channel: 'msfrpc', ok: true }).text,
    'route → msfrpc', 'summarize route decision');
  assert.strictEqual(S({ type: 'belief_update', seq: 3, factor: 'vulns', key: 'CVE-x', host: 'h' }).icon, '🧠', 'summarize belief_update icon');
  assert.strictEqual(S({ type: 'approval_result', seq: 4, approved: false, action: 'pop' }).text, 'denied pop', 'summarize denied approval');
  assert.strictEqual(S({ type: 'approval_result', seq: 5, approved: true, action: 'pop' }).text, 'approved pop', 'summarize approved');
  assert.strictEqual(S({ type: 'run_end', seq: 6, steps: 4 }).text, 'run end (steps=4)', 'summarize run_end');
  assert.strictEqual(S({ type: 'weird', seq: 7 }).text, 'weird', 'summarize unknown type → the type name');
}

// approval markers (R2 TL-5.4): ControlClient approve/deny emit the right command frames
await (async () => {
  const net = await import('node:net');
  const got: string[] = [];
  const server = net.createServer((sock) => {
    sock.setEncoding('utf8');
    let buf = '';
    sock.on('data', (c: string) => {
      buf += c;
      let nl: number;
      while ((nl = buf.indexOf('\n')) !== -1) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (line.trim()) got.push((JSON.parse(line) as { cmd: string }).cmd);
      }
    });
  });
  await new Promise<void>((res) => server.listen(0, '127.0.0.1', () => res()));
  const port = (server.address() as import('node:net').AddressInfo).port;
  await new Promise<void>((resolve) => {
    const c: InstanceType<typeof ControlClient> = new ControlClient({
      onConnect: () => { c.deny(); c.pause(); c.resume(); c.quit(); },
    });
    c.connect(port);
    setTimeout(() => { c.close(); server.close(); resolve(); }, 120);
  });
  assert.deepStrictEqual(got, ['deny', 'pause', 'resume', 'quit'], 'ControlClient helpers emit the right command frames');
})();

fs.rmSync(tmp, { recursive: true, force: true });
console.log('SELFTEST PASS');
