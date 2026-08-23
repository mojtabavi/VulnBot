import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

/** Minimal single-line text field (only mount the ACTIVE one so input isn't shared). */
export function TextField(props: {
  label: string;
  initial?: string;
  mask?: boolean;
  onSubmit: (value: string) => void;
}): React.ReactElement {
  const [value, setValue] = useState(props.initial ?? '');
  useInput((input, key) => {
    if (key.return) {
      props.onSubmit(value);
    } else if (key.backspace || key.delete) {
      setValue((v) => v.slice(0, -1));
    } else if (input && !key.ctrl && !key.meta) {
      setValue((v) => v + input);
    }
  });
  const shown = props.mask ? '*'.repeat(value.length) : value;
  return (
    <Box>
      <Text color="green">{props.label} </Text>
      <Text>{shown}</Text>
      <Text color="gray">▏</Text>
    </Box>
  );
}

/** Type-to-filter select for long lists (e.g. OpenRouter's 300+ models).
 *  ↑/↓ move · type to filter · ⏎ select · Esc cancel. Shows a scrolling window. */
export function FilterSelect(props: {
  title: string;
  items: { label: string; value: string }[];
  onSelect: (value: string) => void;
  onCancel?: () => void;
  windowSize?: number;
}): React.ReactElement {
  const [query, setQuery] = useState('');
  const [i, setI] = useState(0);
  const win = props.windowSize ?? 8;
  const q = query.toLowerCase();
  const filtered = q ? props.items.filter((it) => it.label.toLowerCase().includes(q)) : props.items;
  const clamped = filtered.length === 0 ? 0 : Math.min(i, filtered.length - 1);

  useInput((input, key) => {
    if (key.escape) return props.onCancel?.();
    if (key.return) {
      if (filtered.length > 0) props.onSelect(filtered[clamped].value);
      return;
    }
    const n = Math.max(filtered.length, 1);
    if (key.upArrow) return setI((clamped - 1 + n) % n);
    if (key.downArrow) return setI((clamped + 1) % n);
    if (key.backspace || key.delete) {
      setQuery((v) => v.slice(0, -1));
      setI(0);
      return;
    }
    if (input && !key.ctrl && !key.meta) {
      setQuery((v) => v + input);
      setI(0);
    }
  });

  // scroll window around the cursor
  const start = Math.max(0, Math.min(clamped - Math.floor(win / 2), Math.max(0, filtered.length - win)));
  const view = filtered.slice(start, start + win);

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1}>
      <Text color="cyan">{props.title} (type to filter, ↑↓ move, ⏎ select, Esc cancel)</Text>
      <Text color="gray">
        {'> '}
        {query}
        <Text color="gray">▏</Text>
        {'  '}
        <Text color="gray">
          {filtered.length}/{props.items.length}
        </Text>
      </Text>
      {view.length === 0 ? (
        <Text color="yellow">  no match — Esc to type it manually</Text>
      ) : (
        view.map((it, idx) => {
          const abs = start + idx;
          return (
            <Text key={it.value} color={abs === clamped ? 'cyan' : undefined}>
              {abs === clamped ? '❯ ' : '  '}
              {it.label}
            </Text>
          );
        })
      )}
    </Box>
  );
}

/** Minimal vertical select list. */
export function Select<T extends string>(props: {
  label: string;
  items: { label: string; value: T }[];
  onSelect: (value: T) => void;
}): React.ReactElement {
  const [i, setI] = useState(0);
  useInput((_input, key) => {
    if (key.upArrow) setI((n) => (n - 1 + props.items.length) % props.items.length);
    else if (key.downArrow) setI((n) => (n + 1) % props.items.length);
    else if (key.return) props.onSelect(props.items[i].value);
  });
  return (
    <Box flexDirection="column">
      <Text color="green">{props.label}</Text>
      {props.items.map((it, idx) => (
        <Text key={it.value} color={idx === i ? 'cyan' : undefined}>
          {idx === i ? '❯ ' : '  '}
          {it.label}
        </Text>
      ))}
    </Box>
  );
}
