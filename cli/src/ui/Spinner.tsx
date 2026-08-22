import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';

const FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

/** Claude-Code-style working indicator: braille spinner + verb label + elapsed seconds. */
export default function Spinner({ label }: { label: string }): React.ReactElement {
  const [i, setI] = useState(0);
  const [start] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      setI((x) => (x + 1) % FRAMES.length);
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 80);
    return () => clearInterval(id);
  }, [start]);
  return (
    <Box>
      <Text color="magentaBright">{FRAMES[i]} </Text>
      <Text color="white">{label}</Text>
      <Text color="gray"> ({elapsed}s · esc to interrupt)</Text>
    </Box>
  );
}
