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
