import React, { useEffect, useRef, useState } from 'react';
import { Box, Static, Text, useApp, useInput } from 'ink';
import Banner from './Banner.js';
import { handleCommand, commandMeta, fetchingLabel } from '../commands.js';
import { getModel, loadPrefs, getModelConfig, setModel, setAuthToken, setThinkingLevel } from '../config.js';
import { getProvider, THINKING_LEVELS } from '../providers.js';
import { fetchModels } from '../models.js';
import { beginLogin, completeLogin, openBrowser } from '../oauth.js';
import { runPentest, ensureDb, ensureKali, type PentestRun } from '../executor.js';
import { emptyRunState, parseRunLine, summarizeRun, isMarker, type RunState } from '../run.js';
import { classifyLog, type ClassifiedLog } from '../logfmt.js';
import PipelineLine from './PipelineLine.js';
import { FilterSelect, TextField } from './inputs.js';
import Spinner from './Spinner.js';
import StatusBar from './StatusBar.js';
import SlashMenu, { matchCommands } from './SlashMenu.js';
import BeliefPanel from './BeliefPanel.js';
import RunView from './RunView.js';
import LogLine from './LogLine.js';

type Item =
  | { kind: 'line'; text: string }
  | { kind: 'belief'; runId?: string }
  | { kind: 'banner' }
  | { kind: 'log'; line: ClassifiedLog }; // a styled pipeline log line printed into scrollback
type Picker = { kind: 'model' | 'thinking'; title: string; items: { label: string; value: string }[] };

export default function Repl({
  onSetup,
  autoLogin = false,
  version = '',
}: {
  onSetup: (kind?: 'full' | 'llm') => void;
  /** true when setup chose the Claude subscription — run /login (opens browser) on mount. */
  autoLogin?: boolean;
  /** version string for the banner (shown until the first command). */
  version?: string;
}): React.ReactElement {
  const { exit } = useApp();
  // Transcript items are append-only so Ink's <Static> can print each line ONCE into the terminal's
  // own scrollback — that's what makes the log scrollable + copyable. The banner is the first Static
  // item (not a live element): it prints once at the top and scrolls up into history as commands add
  // output, so it "shows on first run then disappears" without a shrinking live frame (which orphans
  // the previous frame into scrollback — the double-input-box bug).
  const [items, setItems] = useState<Item[]>([{ kind: 'banner' }, { kind: 'line', text: 'type /help to get started.' }]);
  // <Static> renders append-only (tracks how many items it has printed); a clear that shrinks the
  // array would desync it, so we remount Static via this key on every clear to reset that counter.
  const [staticKey, setStaticKey] = useState(0);
  const clearTranscript = () => { setItems([]); setStaticKey((k) => k + 1); };
  const [input, setInput] = useState('');
  const [cursor, setCursor] = useState(0); // caret position within `input` (0..input.length)
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState('Working…');
  const [menuSel, setMenuSel] = useState(0);
  const [hist, setHist] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const [picker, setPicker] = useState<Picker | null>(null);
  // pending OAuth paste-flow secrets (set while we wait for the user to paste the auth code).
  const [oauth, setOauth] = useState<{ verifier: string; state: string; redirectUri: string } | null>(null);
  const didAutoLogin = useRef(false);
  const didEnsureDb = useRef(false);
  const runRef = useRef<PentestRun | null>(null);
  const [running, setRunning] = useState(false);
  // Live run view (phase tree + timers). runStateRef mirrors `run` so onExit can summarize it.
  const [run, setRun] = useState<RunState | null>(null);
  const runStateRef = useRef<RunState | null>(null);

  // Setup chose the Claude subscription → kick off /login automatically (opens the browser),
  // then the model + thinking pickers follow. Runs once.
  useEffect(() => {
    if (autoLogin && !didAutoLogin.current) {
      didAutoLogin.current = true;
      void handleLogin();
    }
  }, [autoLogin]);

  // MySQL = docker → make sure the container is up + tables exist as soon as octopus starts, so it's
  // running and connectable before the first /run (idempotent: silent when already reachable). Runs once.
  useEffect(() => {
    if (didEnsureDb.current) return;
    didEnsureDb.current = true;
    if ((loadPrefs().mysqlMode ?? 'docker') === 'docker') {
      void ensureDb('docker', (line) => pushLines([line]));
    }
  }, []);

  // Append-only (no slice cap): <Static> assumes an append-only list, and dropping the front would
  // desync its render bookkeeping. Transcript lines are one-per-command, so growth is slow.
  const push = (it: Item) => setItems((x) => [...x, it]);
  const pushLines = (ls: string[]) => setItems((x) => [...x, ...ls.map((t) => ({ kind: 'line', text: t } as Item))]);

  /** Replace the whole line + place the caret (default: end). Used by history/tab/clear/submit. */
  const setLine = (text: string, pos: number = text.length): void => {
    setInput(text);
    setCursor(Math.max(0, Math.min(pos, text.length)));
    setMenuSel(0);
  };

  const menuItems = input.startsWith('/') && !input.includes(' ') ? matchCommands(input) : [];
  const menuVisible = menuItems.length > 0;

  function recall(delta: number): void {
    if (hist.length === 0) return;
    let idx = histIdx < 0 ? hist.length : histIdx;
    idx += delta;
    if (idx < 0) idx = 0;
    if (idx >= hist.length) {
      setHistIdx(-1);
      setLine('');
      return;
    }
    setHistIdx(idx);
    setLine(hist[idx]);
  }

  async function submit(text: string): Promise<void> {
    setHist((h) => [...h, text]);
    setHistIdx(-1);
    push({ kind: 'line', text: `❯ ${text}` });

    if (/^\/belief(\s|$)/.test(text)) {
      push({ kind: 'belief', runId: text.split(/\s+/)[1] });
      return;
    }

    const meta = commandMeta(text);
    if (meta.slow) {
      setBusy(true);
      setLabel(meta.label);
    }
    try {
      const res = await handleCommand(text);
      if (res.action === 'clear') clearTranscript();
      else pushLines(res.lines);
      if (res.action === 'quit') return exit();
      if (res.action === 'setup') return onSetup('full');
      if (res.action === 'reconfigure-llm') return onSetup('llm');
      if (res.action === 'pick-model') return await openModelPicker();
      if (res.action === 'login') return await handleLogin();
      if (res.action === 'run-pentest') return await startRun(res.description ?? '');
    } catch (e: any) {
      pushLines([`error: ${e?.message ?? String(e)}`]);
    } finally {
      setBusy(false);
    }
  }

  // ── model overlay picker (provider switching goes through the guided wizard) ──
  async function openModelPicker(): Promise<void> {
    const c = getModelConfig();
    const p = getProvider(c.provider);
    if (!p) {
      pushLines([`no provider set — run /provider first.`]);
      return;
    }
    setBusy(true);
    setLabel(fetchingLabel());
    // under OAuth the bearer lives in auth_token (api_key is empty) — send the right credential.
    const cred = c.auth_mode === 'oauth' ? c.auth_token : c.api_key;
    let list: string[] = [];
    try {
      list = await fetchModels(p, { baseUrl: c.base_url, apiKey: cred, authMode: c.auth_mode });
    } catch {
      list = [];
    } finally {
      setBusy(false);
    }
    if (list.length === 0) {
      // Custom endpoint has a live /models catalog too (once base_url is set), so it gets the same
      // retry/re-check guidance as named providers — no hand-typed model prompt.
      pushLines([
        `couldn't fetch ${p.label} models (check the Base URL / API key / connectivity).`,
        `retry with /model, or re-enter the endpoint via /provider.`,
      ]);
      return;
    }
    setPicker({ kind: 'model', title: `pick a model (${p.label})`, items: list.map((m) => ({ label: m, value: m })) });
  }

  async function handleLogin(): Promise<void> {
    // Claude Pro/Max OAuth (⚠️ grey area, user's own account). Native Anthropic only.
    // Manual paste flow: the public Claude client only accepts Anthropic's console callback and
    // shows the code on-screen (loopback redirect is rejected). We open the URL, then wait for
    // the user to paste the code into the overlay below.
    const c = getModelConfig();
    if (getProvider(c.provider)?.kind !== 'anthropic') {
      pushLines(['/login is for the native Anthropic provider (Claude Pro/Max subscription).', 'switch first: /provider anthropic']);
      return;
    }
    const { url, verifier, state, redirectUri } = beginLogin();
    await openBrowser(url);
    pushLines([
      'opening your browser to sign in to Claude…',
      'after you click Authorize, the page shows a code — copy it and paste below, then Enter.',
      'if the browser did not open, open this URL to sign in:',
      `  ${url}`,
    ]);
    setOauth({ verifier, state, redirectUri }); // mounts the code-paste overlay
  }

  async function submitOauthCode(pasted: string): Promise<void> {
    const pend = oauth;
    setOauth(null);
    if (!pend) return;
    if (!pasted.trim()) {
      pushLines(['sign-in cancelled (no code).', 'the API-key path still works: /provider anthropic → API key.']);
      return;
    }
    setBusy(true);
    setLabel('Exchanging authorization code…');
    try {
      const tokens = await completeLogin(pasted, pend.verifier, pend.redirectUri, pend.state);
      setAuthToken(tokens.access_token); // flips auth_mode: oauth + writes the bearer to model_config.yaml
      pushLines(['signed in — Claude Pro/Max subscription active (auth_mode: oauth).']);
      setBusy(false);
      await openModelPicker(); // fetch the Claude catalog with the bearer + let them pick a model
    } catch (e: any) {
      pushLines([`sign-in failed: ${e?.message ?? String(e)}`, 'the API-key path still works: /provider anthropic → API key.']);
    } finally {
      setBusy(false);
    }
  }

  // ── real pentest run: spawn the Python pipeline + stream its output into the transcript ──
  async function startRun(rawDescription: string): Promise<void> {
    if (runRef.current) {
      pushLines(['a run is already active — Ctrl+C to stop it first.']);
      return;
    }
    // `--agent` anywhere in the args selects the R1 belief-first BeliefAgent loop; strip it from
    // the description passed to the pipeline (default: the legacy 3-phase run).
    const agent = /(^|\s)--agent(\s|$)/.test(rawDescription);
    const description = rawDescription.replace(/(^|\s)--agent(\s|$)/g, ' ').trim();
    if (!description) {
      pushLines(['no target/description — usage: /run [--agent] <target-ip | task>']);
      return;
    }
    // Preflight MySQL: docker mode auto-starts + inits it; local mode reports and bails. This is
    // what turns "MySQL down" into one clear line instead of the old NoneType crash cascade.
    setRunning(true);
    const mysqlMode = loadPrefs().mysqlMode ?? 'docker';
    const { ready } = await ensureDb(mysqlMode, (line) => pushLines([line]));
    if (!ready) {
      setRunning(false);
      pushLines(['run aborted: MySQL not ready.']);
      return;
    }
    // Preflight Kali too: catch an unreachable executor (wrong host / lab down / missing key) here
    // with one clear line, instead of a paramiko `getaddrinfo failed` traceback mid-run.
    const kali = await ensureKali((line) => pushLines([line]));
    if (!kali.ready) {
      setRunning(false);
      pushLines(['run aborted: Kali executor not ready.']);
      return;
    }
    // Fold the pipeline's streamed stdout (progress markers + raw log) into the live RunView
    // instead of dumping every loguru line into the transcript.
    runStateRef.current = emptyRunState(Date.now());
    setRun(runStateRef.current);
    const feed = (line: string): void => {
      // Markers drive the live status box (RunView). Every non-marker line is ALSO streamed into the
      // <Static> transcript as a styled Ink element, so the full run log scrolls in the terminal's
      // own scrollback and stays selectable/copyable (parseRunLine still counts it + keeps the tail).
      const base = runStateRef.current ?? emptyRunState(Date.now());
      const next = parseRunLine(base, line, Date.now());
      runStateRef.current = next;
      setRun(next);
      if (!isMarker(line)) {
        const cl = classifyLog(line);
        if (cl) push({ kind: 'log', line: cl });
      }
    };
    if (agent) pushLines(['belief-agent mode (--agent): standalone POMDP loop.']);
    runRef.current = runPentest(
      description,
      5, // max react steps per phase (or belief-loop step cap in --agent mode)
      feed,
      (code) => {
        const fin = runStateRef.current;
        runRef.current = null;
        runStateRef.current = null;
        setRun(null);
        setRunning(false);
        if (!fin) {
          pushLines([code === null ? 'run stopped.' : `run finished (exit ${code}).`]);
          return;
        }
        // The live panel collapses to one line — but on failure/stop keep its distilled evidence in
        // the transcript so the user can debug from scrollback. Just the deduped warnings (the causes)
        // + a pointer to the full log; the raw tail is redundant + noisy (pipeline chatter).
        const out = [summarizeRun(fin, code, Date.now())];
        if (code !== 0 || fin.error) {
          const seen: string[] = [];
          for (const w of fin.warnings) {
            if (seen.some((s) => s.includes(w) || w.includes(s))) continue; // drop dup/substring
            seen.push(w);
            out.push(`  ⚠ ${w}`);
          }
          out.push('  hint: full trace in logs/Auto-Pentest.log');
        }
        pushLines(out);
      },
      agent,
    );
  }

  function openThinkingPicker(): void {
    setPicker({
      kind: 'thinking',
      title: 'extended-thinking level (Claude)',
      items: THINKING_LEVELS.map((t) => ({ label: t.label, value: t.id })),
    });
  }

  function onPickerSelect(value: string): void {
    const kind = picker?.kind;
    setPicker(null);
    if (kind === 'thinking') {
      setThinkingLevel(value);
      pushLines([`thinking level -> ${value}`]);
      return;
    }
    // model pick
    setModel(value);
    pushLines([`model switched -> ${value} (hot-reloaded on next call)`]);
    // Anthropic models support extended thinking — chain into a thinking-level pick.
    if (getProvider(getModelConfig().provider)?.kind === 'anthropic') openThinkingPicker();
  }

  useInput((ch, key) => {
    if (key.ctrl && ch === 'c') {
      if (runRef.current) {
        runRef.current.stop();
        pushLines(['stopping run…']);
        return;
      }
      return exit();
    }
    if (picker || oauth) return; // an overlay owns the keyboard (its own useInput handles keys)
    if (running) return; // a pentest is streaming — ignore input (ctrl+c stops it)
    if (busy) return; // ignore input while a command runs (ctrl+c still exits)
    if (key.ctrl && ch === 'l') {
      clearTranscript();
      setLine('');
      return;
    }
    if (key.escape) {
      setLine('');
      return;
    }
    if (key.tab) {
      if (menuVisible) {
        const sel = menuItems[((menuSel % menuItems.length) + menuItems.length) % menuItems.length];
        setLine(`/${sel.name}${sel.args ? ' ' : ''}`);
      }
      return;
    }
    if (key.upArrow) return menuVisible ? setMenuSel((s) => s - 1) : recall(-1);
    if (key.downArrow) return menuVisible ? setMenuSel((s) => s + 1) : recall(1);
    // ── caret movement (readline-style) ──
    if (key.leftArrow) return setCursor((c) => Math.max(0, c - 1));
    if (key.rightArrow) return setCursor((c) => Math.min(input.length, c + 1));
    if (key.ctrl && ch === 'a') return setCursor(0); // home
    if (key.ctrl && ch === 'e') return setCursor(input.length); // end
    if (key.return) {
      const t = input.trim();
      setLine('');
      if (t) void submit(t);
      return;
    }
    if (key.backspace || key.delete) {
      // delete the char before the caret (readline backspace)
      setCursor((c) => {
        if (c <= 0) return 0;
        setInput((v) => v.slice(0, c - 1) + v.slice(c));
        return c - 1;
      });
      setMenuSel(0);
      return;
    }
    if (ch && !key.ctrl && !key.meta) {
      // insert typed/pasted text (Ink delivers a paste as one multi-char chunk) at the caret
      setCursor((c) => {
        setInput((v) => v.slice(0, c) + ch + v.slice(c));
        return c + ch.length;
      });
      setMenuSel(0);
    }
  });

  const prefs = loadPrefs();
  return (
    <Box flexDirection="column">
      {/* Printed history: <Static> writes each item once into the terminal's scrollback (above this
          live frame) and never repaints it, so the log scrolls natively and text stays selectable. */}
      <Static key={staticKey} items={items}>
        {(it, i) =>
          it.kind === 'banner' ? (
            <Banner key={i} version={version} />
          ) : it.kind === 'belief' ? (
            <BeliefPanel key={i} runId={it.runId} />
          ) : it.kind === 'log' ? (
            <PipelineLine key={i} line={it.line} />
          ) : (
            <LogLine key={i} text={it.text} />
          )
        }
      </Static>
      {run ? <RunView state={run} /> : busy ? <Spinner label={label} /> : null}
      {picker ? (
        <FilterSelect
          title={picker.title}
          items={picker.items}
          onSelect={onPickerSelect}
          onCancel={() => {
            setPicker(null);
            pushLines(['cancelled.']);
          }}
        />
      ) : null}
      {oauth ? (
        <TextField label="paste the authorization code (then Enter):" onSubmit={submitOauthCode} />
      ) : null}
      <Box borderStyle="round" borderColor={busy ? 'gray' : 'magenta'} paddingX={1}>
        <Text color="magenta">❯ </Text>
        {busy || running ? (
          <Text>{input}</Text>
        ) : (
          <>
            <Text>{input.slice(0, cursor)}</Text>
            <Text inverse>{input.slice(cursor, cursor + 1) || ' '}</Text>
            <Text>{input.slice(cursor + 1)}</Text>
          </>
        )}
      </Box>
      {menuVisible ? <SlashMenu input={input} selected={menuSel} /> : null}
      <StatusBar
        executor={prefs.executorMode}
        model={getModel()}
        hint={running ? 'pentest running… ctrl+c to stop' : busy ? label : '/ commands · ↑ history · tab complete · ctrl+l clear · ctrl+c quit'}
      />
    </Box>
  );
}
