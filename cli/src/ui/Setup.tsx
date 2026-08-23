import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { TextField, Select, FilterSelect } from './inputs.js';
import {
  writeModelConfig,
  writeKaliConfig,
  savePrefs,
  loadPrefs,
  listProviders,
  type ExecutorMode,
} from '../config.js';
import { getProvider, type AuthMode } from '../providers.js';
import { fetchModels } from '../models.js';

type Step =
  | 'executor'
  | 'khost'
  | 'kport'
  | 'kuser'
  | 'kpass'
  | 'provider'
  | 'auth'
  | 'api_key'
  | 'model_fetch'
  | 'model_pick'
  | 'model_manual';

interface Draft {
  mode: ExecutorMode;
  host: string;
  port: string;
  user: string;
  pass: string;
  providerId: string;
  base_url: string;
  api_key: string;
  auth_mode: AuthMode;
  model: string;
}

const DEFAULT: Draft = {
  mode: 'docker',
  host: '',
  port: '22',
  user: 'root',
  pass: '',
  providerId: 'openai',
  base_url: '',
  api_key: '',
  auth_mode: 'api_key',
  model: '',
};

export default function Setup({ onDone }: { onDone: () => void }): React.ReactElement {
  const [step, setStep] = useState<Step>('executor');
  const [d, setD] = useState<Draft>(DEFAULT);
  const [models, setModels] = useState<string[]>([]);
  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }));

  function finalize(draft: Draft): void {
    const p = getProvider(draft.providerId);
    writeModelConfig({
      provider: draft.providerId,
      kind: p?.kind ?? 'openai',
      base_url: draft.base_url,
      api_key: draft.api_key,
      model: draft.model,
      auth_mode: draft.auth_mode,
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

  // Enter the LLM flow at the provider picker with a fresh draft carrying the chosen executor.
  function afterProvider(id: string): void {
    const p = getProvider(id)!;
    set({ providerId: id, base_url: p.baseUrl, auth_mode: p.authModes[0] });
    if (p.authModes.length > 1) setStep('auth');
    else if (p.authModes[0] === 'none') setStep('model_fetch');
    else setStep('api_key');
  }

  // Fetch the catalog when we reach model_fetch; branch to picker or manual entry.
  useEffect(() => {
    if (step !== 'model_fetch') return;
    const p = getProvider(d.providerId)!;
    let alive = true;
    fetchModels(p, { baseUrl: d.base_url, apiKey: d.api_key, authMode: d.auth_mode })
      .then((list) => {
        if (!alive) return;
        setModels(list);
        setStep(list.length > 0 ? 'model_pick' : 'model_manual');
      })
      .catch(() => alive && setStep('model_manual'));
    return () => {
      alive = false;
    };
  }, [step]);

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
        <Select<string>
          label="LLM provider:"
          items={listProviders().map((p) => ({ label: p.label, value: p.id }))}
          onSelect={afterProvider}
        />
      )}

      {step === 'auth' && (
        <Select<AuthMode>
          label={`Auth for ${getProvider(d.providerId)?.label}:`}
          items={(getProvider(d.providerId)?.authModes ?? ['api_key']).map((m) => ({
            label:
              m === 'oauth'
                ? 'Subscription (Claude Pro/Max — OAuth; run /login after setup)'
                : m === 'none'
                ? 'None (local)'
                : 'API key',
            value: m,
          }))}
          onSelect={(m) => {
            set({ auth_mode: m });
            if (m === 'api_key') setStep('api_key');
            else setStep('model_fetch'); // oauth token added later via /login (B6); none = no key
          }}
        />
      )}

      {step === 'api_key' && (
        <TextField key="api_key" label={`${getProvider(d.providerId)?.label} API key (blank if none):`} mask
          onSubmit={(v) => { set({ api_key: v }); setStep('model_fetch'); }} />
      )}

      {step === 'model_fetch' && (
        <Text color="gray">fetching {getProvider(d.providerId)?.label} models…</Text>
      )}

      {step === 'model_pick' && (
        <FilterSelect
          title={`pick a model (${getProvider(d.providerId)?.label})`}
          items={models.map((m) => ({ label: m, value: m }))}
          onSelect={(v) => finalize({ ...d, model: v })}
          onCancel={() => setStep('model_manual')}
        />
      )}

      {step === 'model_manual' && (
        <TextField
          key="model"
          label={`Model name (e.g. ${getProvider(d.providerId)?.modelHint ?? 'model-id'}):`}
          initial={d.model}
          onSubmit={(v) => finalize({ ...d, model: v })}
        />
      )}
    </Box>
  );
}
