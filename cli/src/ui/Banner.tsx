import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';

// Braille octopus. The first + last two rows are the decorative ring arcs — we drop them,
// then trim blank margin columns so it's smaller. Head stays static; only the lower (leg)
// rows sway, so the tentacles really move.
const RAW = [
  '⠀⠀⠀⠀⠀             ⠀⠀ ⠀⢀⣠⣤⣤⣤⣤⣤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀          ⠀⠀ ⠀ ⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀        ⠀⠀⠀⠀⠀⠀  ⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀      ⠀⣀⣤⣤⣄⣀⠀⠀  ⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⢀⣀⣤⣤⣄⣀⡀⠀⠀',
  '⠀      ⣶⡟⠛⠉⠉⠛⢿⣷⡆⠀ ⢸⣿⡿⢿⣿⣿⣿⣿⣿⡿⢿⣿⠁⠀⠀⣶⣿⠟⠋⠉⠉⠛⣷⣆⠀⠀',
  '⠀     ⣸⡯⠀⠀⠀⠀⠀⠈⣿⣿⡇ ⠀⣸⣿⠀⠀⢈⣻⣿⣏⠁⠀⢀⣿⡀⠀⢾⣿⡏⠀⠀⠀ ⠀⠀⠠⣿⡄⠀',
  '     ⠀⢿⣷⣆⡀⠀⢀⡤⠀⢸⣿⣷⠀⢹⣿⣷⣾⣿⠏⠀⢿⣿⣾⣿⣿⠁⢰⣿⣿⠃⠀⢄⠀⠀⣀⣲⣿⡇⡀',
  '     ⠀⠈⠙⠿⠟⠛⠁⠀⠀⠀⠻⢿⣧⣤⣤⠈⣽⣿⣷⣿⣿⣿⡏⢠⣤⣤⣾⡿⠋⠀⠀⠀⠙⠛⠿⠟⠋⠁⠀',
  '    ⠀⠀⢠⣶⣶⣿⣿⣿⣷⣶⣾⣦⣤⡈⠛⠛⠓⣀⣙⠛⠘⢙⣡⡀⠛⠛⡋⢡⣤⣶⣷⣶⣿⣿⣿⣿⣶⣦⡀⠀',
  '     ⠀⣿⣿⣿⠟⠋⠉⠉⠉⠛⠿⣿⣿⣿⣴⣾⡿⠟⢃⢀⡙⠻⣿⣷⣼⣿⣿⡿⠟⠛⠉⠉⠉⠙⠻⣿⣿⡇⠀',
  '     ⠀⣿⡟⠁⠀⠀⠀⠀⠀⢀⠀⠀⠉⠉⠉⣡⣀⣼⣿⠰⣿⣆⣠⡈⠉⠉⠁⠀⢠⠀⠀⠀  ⠀⠀⠀⠙⣿⣏⠀',
  '     ⠀⢿⡏⠀⠀⠀⠀⠀⠀⢈⡇⢀⣠⣾⣾⣿⣿⡿⠋⠀⠻⣿⣿⣿⣶⣧⣄⠀⣏⠀⠀⠀  ⠀⠀⠀⠀⣿⡇',
  '⠀     ⠘⣿⣇⣀⠀⠀⠀⣀⣼⢁⣾⡿⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⠉⠉⠻⣿⣧⠹⣅⡀⠀  ⠀⠀⣀⣺⡿⠀⠀',
  '⠀      ⠙⣿⣿⣦⣿⣶⣿⢃⣾⡏⠀⠀⠀⠀⠈⠶⣄⠀⣴⠆⠀⠀⠀⠀⠈⢿⣦⢹⣷⣾⣷⣾⣿⡿⠁⠀⠀',
  '⠀⠀      ⠈⠻⠿⠿⠛⠃⣾⣿⠀⠀⠀⠀⠀⠀⠀⣿⠐⡗⠀⠀⠀⠀⠀⠀⢸⣿⡆⠙⠻⠿⠿⠋⠀⠀⠀',
  '⠀⠀⠀        ⠀⠀⠀⠀⠻⣿⣧⣀⠀⠀⠀⢀⣸⣿⢈⣿⡂⠀⠀⠀⢀⣀⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀         ⠀⠀⠀⠈⠻⣿⣷⣿⣶⣿⣿⠇⠀⢿⣿⣷⣾⣷⣾⡿⠟⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠀          ⠀⠀⠙⠛⠻⠟⠋⠀⠀⠀⠀⠀⠀',
]

// Show the art exactly as-is (no crop/trim). Only the lower rows sway to move the legs.
const ART = RAW;
const LEG_START = Math.ceil(ART.length * 0.5); // lower half = tentacles
const AMP_MAX = 2;

function legAmp(row: number): number {
  if (row < LEG_START) return 0;
  const t = (row - LEG_START) / Math.max(1, ART.length - 1 - LEG_START);
  return Math.max(1, Math.round(t * AMP_MAX));
}

export default function Banner({ version, animate = true }: { version: string; animate?: boolean }): React.ReactElement {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (!animate) return;
    const id = setInterval(() => setT((x) => x + 1), 150);
    return () => clearInterval(id);
  }, [animate]);

  return (
    <Box flexDirection="column" marginBottom={1}>
      {ART.map((line, i) => {
        const amp = legAmp(i);
        const sway = animate ? Math.round(amp * Math.sin(t * 0.5 + i * 0.8)) : 0;
        const indent = ' '.repeat(AMP_MAX + sway); // head rows: amp 0 → fixed indent
        return (
          <Text key={i} color="magentaBright">
            {indent}
            {line}
          </Text>
        );
      })}
      <Text color="magentaBright" bold>{'  OCTOPUS'}</Text>
      <Text color="gray">{'  belief-state pentest agent · v'}{version}</Text>
    </Box>
  );
}
