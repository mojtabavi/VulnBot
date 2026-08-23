import React from 'react';
import { Box, Text } from 'ink';

// Octopus art. Stored with its original padding; the component strips surrounding blank rows and
// the common left margin at load so it renders compact (no huge whitespace border).
const RAW_ART = String.raw`
                                    ██████████████████
                                █████████████████████████
                               ███████████████████████████
                             ███████████████████████████████
                            █████████████████████████████████
                           ████████████████████████████████████
                          █████████████████████████████████████
                           ████████████████████████████████████
                          █████████████████████████████████████
                           ████████████████████████████████████
                           █ ███████████████████████████████ █
                              ██████████████████████████████
                                 █████████████████████ █
                                    █ █████░████████ █
                            █████     ██████████████    █████
                             ████████     ██████     ████████
                               ██ █       █ ██ █     █ █ █
                                        █   █   ██
                                    ███            ███
                               ██████   ██████████   ██████
                          █████████ █████████ ████████░█ ███████
                     ░██████████████████████████████████████████████
                    ██████       ██████████    █████████       ██████
                   █████       ████████           █████████       ████
                   █░█       ████████               ████████       ███
                   ███       ████████                ███████       ███
                     ██      ██████                  ███████       ██
                      ██      ███████                ██████       █
                       ██      ██████               ███████      ██
                                 ██████            █████
                                   ████           ████
                               █      ██         ███     ██
                                      ██          ██
                                     ██            █
                                    ██              █
                                                    █`;

/** Drop leading/trailing blank rows, then strip the common left indent so the art is compact. */
function trimArt(raw: string): string[] {
  let lines = raw.replace(/\n$/, '').split('\n');
  while (lines.length && lines[0].trim() === '') lines = lines.slice(1);
  while (lines.length && lines[lines.length - 1].trim() === '') lines = lines.slice(0, -1);
  const indent = Math.min(
    ...lines.filter((l) => l.trim() !== '').map((l) => l.match(/^ */)![0].length),
  );
  return lines.map((l) => l.slice(indent).replace(/\s+$/, ''));
}

const ART = trimArt(RAW_ART);

export default function Banner({ version }: { version: string; animate?: boolean }): React.ReactElement {
  return (
    <Box flexDirection="column" marginBottom={1}>
      {ART.map((line, i) => (
        <Text key={i} color="magentaBright">
          {line}
        </Text>
      ))}
      <Text color="magentaBright" bold>{'  OCTOPUS'}</Text>
      <Text color="gray">{'  belief-state pentest agent · v'}{version}</Text>
    </Box>
  );
}
