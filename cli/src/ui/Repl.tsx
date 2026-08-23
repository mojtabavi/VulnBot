import React, { useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import { handleCommand, commandMeta, fetchingLabel } from '../commands.js';
import { getModel, loadPrefs, getModelConfig, setModel, setProvider, setAuthToken } from '../config.js';
import { getProvider, listProviders } from '../providers.js';
import { fetchModels } from '../models.js';
import { login as oauthLogin } from '../oauth.js';
import { FilterSelect } from './inputs.js';
import Spinner from './Spinner.js';
import StatusBar from './StatusBar.js';
import SlashMenu, { matchCommands } from './SlashMenu.js';
import BeliefPanel from './BeliefPanel.js';

type Item = { kind: 'line'; text: string } | { kind: 'belief'; runId?: string };
type Picker = { kind: 'model' | 'provider'; title: string; items: { label: string; value: string }[] };

export default function Repl({ onSetup }: { onSetup: () => void }): React.ReactElement {
  const { exit } = useApp();
  const [items, setItems] = useState<Item[]>([{ kind: 'line', text: 'type /help to get started.' }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState('Working…');
  const [menuSel, setMenuSel] = useState(0);
  const [hist, setHist] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const [picker, setPicker] = useState<Picker | null>(null);

  const push = (it: Item) => setItems((x) => [...x, it].slice(-200));
  const pushLines = (ls: string[]) => setItems((x) => [...x, ...ls.map((t) => ({ kind: 'line', text: t } as Item))].slice(-200));

  const menuItems = input.startsWith('/') && !input.includes(' ') ? matchCommands(input) : [];
  const menuVisible = menuItems.length > 0;

  function recall(delta: number): void {
    if (hist.length === 0) return;
    let idx = histIdx < 0 ? hist.length : histIdx;
    idx += delta;
    if (idx < 0) idx = 0;
    if (idx >= hist.length) {
      setHistIdx(-1);
      setInput('');
      return;
    }
    setHistIdx(idx);
    setInput(hist[idx]);
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
      if (res.action === 'clear') setItems([]);
      else pushLines(res.lines);
      if (res.action === 'quit') return exit();
      if (res.action === 'setup') return onSetup();
      if (res.action === 'pick-provider') return openProviderPicker();
      if (res.action === 'pick-model') return await openModelPicker();
      if (res.action === 'login') return await handleLogin();
    } catch (e: any) {
      pushLines([`error: ${e?.message ?? String(e)}`]);
    } finally {
      setBusy(false);
    }
  }

  // ── provider/model overlay pickers ────────────────────────────────────────
  function openProviderPicker(): void {
    setPicker({
      kind: 'provider',
      title: 'pick a provider',
      items: listProviders().map((p) => ({ label: p.label, value: p.id })),
    });
  }

  async function openModelPicker(): Promise<void> {
    const c = getModelConfig();
    const p = getProvider(c.provider);
    if (!p) {
      pushLines([`no provider set — run /provider first.`]);
      return;
    }
    setBusy(true);
    setLabel(fetchingLabel());
    let list: string[] = [];
    try {
      list = await fetchModels(p, { baseUrl: c.base_url, apiKey: c.api_key, authMode: c.auth_mode });
    } catch {
      list = [];
    } finally {
      setBusy(false);
    }
    if (list.length === 0) {
      pushLines([
        `no live catalog for ${p.label} (offline / no key / not supported).`,
        `set it directly: /model <name>   e.g. /model ${p.modelHint ?? 'model-id'}`,
      ]);
      return;
    }
    setPicker({ kind: 'model', title: `pick a model (${p.label})`, items: list.map((m) => ({ label: m, value: m })) });
  }

  async function handleLogin(): Promise<void> {
    // Claude Pro/Max OAuth (⚠️ grey area, user's own account). Native Anthropic only.
    const c = getModelConfig();
    if (getProvider(c.provider)?.kind !== 'anthropic') {
      pushLines(['/login is for the native Anthropic provider (Claude Pro/Max subscription).', 'switch first: /provider anthropic']);
      return;
    }
    setBusy(true);
    setLabel('Waiting for browser sign-in…');
    try {
      const { tokens } = await oauthLogin({
        onUrl: (url) =>
          pushLines(['opening your browser to sign in to Claude…', 'if it did not open, paste this URL:', `  ${url}`]),
      });
      setAuthToken(tokens.access_token); // flips auth_mode: oauth + writes the bearer to model_config.yaml
      pushLines([
        'signed in — Claude Pro/Max subscription active (auth_mode: oauth).',
        'pick a model: /model',
        tokens.refresh_token ? '(token will need /login again after it expires)' : '',
      ].filter(Boolean));
    } catch (e: any) {
      pushLines([`sign-in failed: ${e?.message ?? String(e)}`, 'the API-key path still works: /provider anthropic then /setup.']);
    } finally {
      setBusy(false);
    }
  }

  function onPickerSelect(value: string): void {
    const kind = picker?.kind;
    setPicker(null);
    if (kind === 'model') {
      setModel(value);
      pushLines([`model switched -> ${value} (hot-reloaded on next call)`]);
    } else if (kind === 'provider') {
      setProvider(value);
      const p = getProvider(value)!;
      pushLines([`provider -> ${p.label}`]);
      // chain straight into model selection for the new provider.
      void openModelPicker();
    }
  }

  useInput((ch, key) => {
    if (key.ctrl && ch === 'c') return exit();
    if (picker) return; // overlay owns the keyboard (its own useInput handles keys + Esc)
    if (busy) return; // ignore input while a command runs (ctrl+c still exits)
    if (key.ctrl && ch === 'l') {
      setItems([]);
      setInput('');
      return;
    }
    if (key.escape) {
      setInput('');
      return;
    }
    if (key.tab) {
      if (menuVisible) {
        const sel = menuItems[((menuSel % menuItems.length) + menuItems.length) % menuItems.length];
        setInput(`/${sel.name}${sel.args ? ' ' : ''}`);
      }
      return;
    }
    if (key.upArrow) return menuVisible ? setMenuSel((s) => s - 1) : recall(-1);
    if (key.downArrow) return menuVisible ? setMenuSel((s) => s + 1) : recall(1);
    if (key.return) {
      const t = input.trim();
      setInput('');
      if (t) void submit(t);
      return;
    }
    if (key.backspace || key.delete) {
      setInput((v) => v.slice(0, -1));
      setMenuSel(0);
      return;
    }
    if (ch && !key.ctrl && !key.meta) {
      setInput((v) => v + ch);
      setMenuSel(0);
    }
  });

  const prefs = loadPrefs();
  return (
    <Box flexDirection="column">
      {items.map((it, i) =>
        it.kind === 'belief' ? <BeliefPanel key={i} runId={it.runId} /> : <Text key={i}>{it.text}</Text>
      )}
      {busy ? <Spinner label={label} /> : null}
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
      <Box borderStyle="round" borderColor={busy ? 'gray' : 'magenta'} paddingX={1}>
        <Text color="magenta">❯ </Text>
        <Text>{input}</Text>
        <Text color="gray">{busy ? '' : '▏'}</Text>
      </Box>
      {menuVisible ? <SlashMenu input={input} selected={menuSel} /> : null}
      <StatusBar
        executor={prefs.executorMode}
        model={getModel()}
        hint={busy ? label : '/ commands · ↑ history · tab complete · ctrl+l clear · ctrl+c quit'}
      />
    </Box>
  );
}
