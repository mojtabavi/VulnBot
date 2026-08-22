import React, { useState } from 'react';
import { Box, Text } from 'ink';
import { TextField, Select } from './inputs.js';
import {
  writeModelConfig,
  writeKaliConfig,
  savePrefs,
  loadPrefs,
  type ExecutorMode,
} from '../config.js';

type Step = 'executor' | 'khost' | 'kport' | 'kuser' | 'kpass' | 'provider' | 'base_url' | 'api_key' | 'model';

interface Draft {
  mode: ExecutorMode;
  host: string;
  port: string;
  user: string;
  pass: string;
  provider: 'openai' | 'ollama';
  base_url: string;
  api_key: string;
  model: string;
}

const DEFAULT: Draft = {
  mode: 'docker',
  host: '',
  port: '22',
  user: 'root',
  pass: '',
  provider: 'openai',
  base_url: 'http://127.0.0.1:11434/v1',
  api_key: '',
  model: '',
};

export default function Setup({ onDone }: { onDone: () => void }): React.ReactElement {
  const [step, setStep] = useState<Step>('executor');
  const [d, setD] = useState<Draft>(DEFAULT);
  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }));

  function finalize(draft: Draft): void {
    writeModelConfig({
      provider: draft.provider,
      base_url: draft.base_url,
      api_key: draft.api_key,
      model: draft.model,
    });
    if (draft.mode === 'remote') {
      writeKaliConfig(
        { hostname: draft.host, port: parseInt(draft.port || '22', 10), username: draft.user, password: draft.pass },
        'remote'
      );
    } else if (draft.mode === 'docker') {
      // Python agent reaches the container over the compose network; placeholder host.
      writeKaliConfig({ hostname: 'kali-tools', port: 22, username: 'root', password: '' }, 'docker');
    }
    const prefs = loadPrefs();
    savePrefs({ ...prefs, setupComplete: true, executorMode: draft.mode, model: draft.model });
    onDone();
  }

  return (
    <Box flexDirection="column">
      <Text color="yellow">first-time setup</Text>

      {step === 'executor' && (
        <Select<ExecutorMode>
          label="Where does Kali (the executor) run?"
          items={[
            { label: 'Docker container (compose kali-tools) — recommended', value: 'docker' },
            { label: 'Remote host at a specific IP (SSH)', value: 'remote' },
            { label: 'This machine is Kali (local exec — wiring pending)', value: 'local' },
          ]}
          onSelect={(mode) => {
            set({ mode });
            setStep(mode === 'remote' ? 'khost' : 'provider');
          }}
        />
      )}

      {step === 'khost' && (
        <TextField key="khost" label="Kali host/IP:" initial={d.host}
          onSubmit={(v) => { set({ host: v }); setStep('kport'); }} />
      )}
      {step === 'kport' && (
        <TextField key="kport" label="Kali SSH port:" initial={d.port}
          onSubmit={(v) => { set({ port: v || '22' }); setStep('kuser'); }} />
      )}
      {step === 'kuser' && (
        <TextField key="kuser" label="Kali SSH username:" initial={d.user}
          onSubmit={(v) => { set({ user: v || 'root' }); setStep('kpass'); }} />
      )}
      {step === 'kpass' && (
        <TextField key="kpass" label="Kali SSH password (blank if key-based):" mask
          onSubmit={(v) => { set({ pass: v }); setStep('provider'); }} />
      )}

      {step === 'provider' && (
        <Select<'openai' | 'ollama'>
          label="LLM API type:"
          items={[
            { label: 'OpenAI-compatible (vLLM / LM Studio / OpenAI / gateway)', value: 'openai' },
            { label: 'Ollama', value: 'ollama' },
          ]}
          onSelect={(provider) => {
            const base_url = provider === 'ollama' ? 'http://127.0.0.1:11434' : 'http://127.0.0.1:11434/v1';
            set({ provider, base_url });
            setStep('base_url');
          }}
        />
      )}
      {step === 'base_url' && (
        <TextField key="base_url" label="LLM base_url:" initial={d.base_url}
          onSubmit={(v) => { set({ base_url: v || d.base_url }); setStep('api_key'); }} />
      )}
      {step === 'api_key' && (
        <TextField key="api_key" label="LLM api_key (blank if none):" mask
          onSubmit={(v) => { set({ api_key: v }); setStep('model'); }} />
      )}
      {step === 'model' && (
        <TextField key="model" label="LLM model name:" initial={d.model}
          onSubmit={(v) => finalize({ ...d, model: v })} />
      )}
    </Box>
  );
}
