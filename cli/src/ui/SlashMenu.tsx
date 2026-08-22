import React from 'react';
import { Box, Text } from 'ink';
import { COMMANDS } from '../commands.js';

/** Filter commands by the text typed after '/'. */
export function matchCommands(input: string) {
  if (!input.startsWith('/')) return [];
  const q = input.slice(1).split(/\s+/)[0].toLowerCase();
  return COMMANDS.filter((c) => c.name.startsWith(q));
}

/** Live slash-command menu with a highlighted selection (Tab/Enter completes). */
export default function SlashMenu({ input, selected }: { input: string; selected: number }): React.ReactElement | null {
  const items = matchCommands(input);
  if (items.length === 0) return null;
  const sel = ((selected % items.length) + items.length) % items.length;
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="magenta" paddingX={1}>
      {items.map((c, i) => (
        <Text key={c.name} color={i === sel ? 'black' : 'white'} backgroundColor={i === sel ? 'magenta' : undefined}>
          {`/${c.name} ${c.args}`.padEnd(20)}
          <Text color={i === sel ? 'black' : 'gray'}> {c.help}</Text>
        </Text>
      ))}
    </Box>
  );
}
