import React, { useState } from 'react';
import { Box } from 'ink';
import Banner from './ui/Banner.js';
import Setup from './ui/Setup.js';
import Repl from './ui/Repl.js';
import { isFirstRun } from './config.js';

export default function App({ version }: { version: string }): React.ReactElement {
  const [mode, setMode] = useState<'setup' | 'repl'>(isFirstRun() ? 'setup' : 'repl');
  // 'full' = executor+kali+LLM wizard; 'llm' = just re-run the provider/model sub-flow.
  const [kind, setKind] = useState<'full' | 'llm'>('full');
  // set when setup chose the Claude subscription → the REPL auto-runs /login on mount.
  const [autoLogin, setAutoLogin] = useState(false);
  return (
    <Box flexDirection="column">
      {mode === 'setup' ? (
        // First-time setup / reconfig: the banner heads the wizard.
        <>
          <Banner version={version} />
          <Setup
            onDone={(opts) => {
              setAutoLogin(!!opts?.login);
              setMode('repl');
            }}
            startAt={kind === 'llm' ? 'provider' : 'executor'}
            llmOnly={kind === 'llm'}
          />
        </>
      ) : (
        // REPL owns the banner so it can drop it after the first command (see Repl).
        <Repl
          version={version}
          autoLogin={autoLogin}
          onSetup={(k = 'full') => {
            setKind(k);
            setMode('setup');
          }}
        />
      )}
    </Box>
  );
}
