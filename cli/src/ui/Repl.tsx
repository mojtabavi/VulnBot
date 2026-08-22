import React, { useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import { handleCommand, commandMeta } from '../commands.js';
import { getModel, loadPrefs } from '../config.js';
import Spinner from './Spinner.js';
import StatusBar from './StatusBar.js';
import SlashMenu, { matchCommands } from './SlashMenu.js';
import BeliefPanel from './BeliefPanel.js';

type Item = { kind: 'line'; text: string } | { kind: 'belief'; runId?: string };

export default function Repl({ onSetup }: { onSetup: () => void }): React.ReactElement {
  const { exit } = useApp();
  const [items, setItems] = useState<Item[]>([{ kind: 'line', text: 'type /help to get started.' }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState('Working…');
  const [menuSel, setMenuSel] = useState(0);
  const [hist, setHist] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);

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
    } catch (e: any) {
      pushLines([`error: ${e?.message ?? String(e)}`]);
    } finally {
      setBusy(false);
    }
  }

  useInput((ch, key) => {
    if (key.ctrl && ch === 'c') return exit();
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
