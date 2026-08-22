import React, { useState } from 'react';
import { Box } from 'ink';
import Banner from './ui/Banner.js';
import Setup from './ui/Setup.js';
import Repl from './ui/Repl.js';
import { isFirstRun } from './config.js';

export default function App({ version }: { version: string }): React.ReactElement {
  const [mode, setMode] = useState<'setup' | 'repl'>(isFirstRun() ? 'setup' : 'repl');
  return (
    <Box flexDirection="column">
      <Banner version={version} />
      {mode === 'setup' ? <Setup onDone={() => setMode('repl')} /> : <Repl onSetup={() => setMode('setup')} />}
    </Box>
  );
}
