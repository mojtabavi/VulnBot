import React from 'react';
import { Box, Text } from 'ink';
import { beliefView } from '../belief.js';

const WIDTH = 12;
/** A 12-cell filled/empty probability bar. Exported so the live RunView belief panel matches. */
export function bar(p: number, width: number = WIDTH): string {
  const n = Math.round(Math.max(0, Math.min(1, p)) * width);
  return '▇'.repeat(n) + '▁'.repeat(width - n);
}
/** Probability → Ink color (green confident / yellow uncertain / gray low). */
export function color(p: number): string {
  if (p >= 0.6) return 'green';
  if (p >= 0.3) return 'yellow';
  return 'gray';
}

/** Render the latest belief as colored probability bars per hypothesis. */
export default function BeliefPanel({ runId }: { runId?: string }): React.ReactElement {
  const v = beliefView(runId);
  if (!v.runId) return <Text color="gray">(no belief traces yet — run an episode first)</Text>;
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1}>
      <Text color="cyan">belief · run {v.runId} · step {v.step}</Text>
      {v.factors.length === 0 ? <Text color="gray">  (no hosts in belief yet)</Text> : null}
      {v.factors.map((f, i) => (
        <Box key={i} flexDirection="column">
          <Text color="white">{f.host} · {f.name}</Text>
          {Object.entries(f.dist)
            .sort((a, b) => b[1] - a[1])
            .map(([hyp, p]) => (
              <Text key={hyp}>
                {'  '}
                <Text color="gray">{hyp.padEnd(9)}</Text>
                <Text color={color(p)}>{bar(p)}</Text>
                <Text color="gray"> {p.toFixed(2)}</Text>
              </Text>
            ))}
        </Box>
      ))}
      {v.last ? <Text color="gray">last: {v.last}</Text> : null}
    </Box>
  );
}
