import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { TextField, Select, FilterSelect } from './inputs.js';
import {
  writeModelConfig,
  writeKaliConfig,
  writeDbConfig,
  getDbConfig,
  DEFAULT_DB,
  savePrefs,
  loadPrefs,
  listProviders,
  type ExecutorMode,
  type MysqlMode,
} from '../config.js';
import { getProvider, firstLlmStep, stepAfterBaseUrl, THINKING_LEVELS, type AuthMode } from '../providers.js';
import { fetchModels } from '../models.js';

type Step =
  | 'executor'
  | 'khost'
  | 'kport'
  | 'kuser'
  | 'kpass'
  | 'provider'
  | 'base_url'
  | 'auth'
  | 'api_key'
  | 'model_fetch'
  | 'model_pick'
  | 'model_manual'
  | 'model_error'
  | 'thinking'
  | 'mysql';

/** Only the custom endpoint accepts a hand-typed model id; every named provider must pick from
 *  its live /models catalog. */
const CUSTOM_PROVIDER = 'openai-compatible';

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
  auth_token: string;
  model: string;
  thinking_level: string;
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
  auth_token: '',
  model: '',
  thinking_level: 'off',
};

export default function Setup({
  onDone,
  startAt = 'executor',
  llmOnly = false,
}: {
  /** `opts.login` = the config uses the Claude subscription; the REPL should run /login next. */
  onDone: (opts?: { login?: boolean }) => void;
  /** entry step — 'provider' re-runs just the LLM sub-flow (used by /provider, /setup llm). */
  startAt?: Step;
  /** true = only rewrite the LLM config; preserve the existing executor/kali setup. */
  llmOnly?: boolean;
}): React.ReactElement {
  const [step, setStep] = useState<Step>(startAt);
  const [d, setD] = useState<Draft>(DEFAULT);
  const [models, setModels] = useState<string[]>([]);
  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }));

  /** Write the LLM config, then branch: LLM-only reconfig finishes here; a full setup still needs
   *  the MySQL provisioning choice, so it routes to the `mysql` step (commit() finishes it). */
  function finalize(draft: Draft): void {
    const p = getProvider(draft.providerId);
    writeModelConfig({
      provider: draft.providerId,
      kind: p?.kind ?? 'openai',
      base_url: draft.base_url,
      api_key: draft.api_key,
      model: draft.model,
      auth_mode: draft.auth_mode,
      auth_token: draft.auth_token,
      thinking_level: draft.thinking_level,
    });
    if (llmOnly) {
      // LLM-only reconfig: keep the current executor/kali/mysql; just remember the model.
      const login = p?.kind === 'anthropic' && draft.auth_mode === 'oauth';
      const prefs = loadPrefs();
      savePrefs({ ...prefs, setupComplete: true, model: draft.model });
      onDone({ login });
      return;
    }
    setD(draft); // stash the finished draft; the mysql step reads it, then commit() finishes setup
    setStep('mysql');
  }

  /** Finish a full setup: write executor/kali + db config, persist prefs (incl. mysqlMode). */
  function commit(draft: Draft, mysqlMode: MysqlMode): void {
    const p = getProvider(draft.providerId);
    // Anthropic subscription: no model was picked yet (no token during setup) — the REPL runs
    // /login next, which opens the browser, then fetches the catalog + lets the user pick.
    const login = p?.kind === 'anthropic' && draft.auth_mode === 'oauth';
    if (draft.mode === 'remote') {
      writeKaliConfig(
        { hostname: draft.host, port: parseInt(draft.port || '22', 10), username: draft.user, password: draft.pass },
        'remote'
      );
    } else if (draft.mode === 'docker') {
      // The pipeline runs on the HOST and SSHes to kali over the published loopback port
      // (127.0.0.1:2222, see docker-compose). kali-tools' sshd is key-only — point at the agent key.
      writeKaliConfig(
        { hostname: '127.0.0.1', port: 2222, username: 'root', password: '', key_filename: 'docker/agent/keys/agent_ed25519' },
        'docker',
      );
    }
    // docker → loopback defaults matching the mysql compose service; local → keep existing (or defaults).
    writeDbConfig(mysqlMode === 'docker' ? DEFAULT_DB : getDbConfig());
    const prefs = loadPrefs();
    savePrefs({ ...prefs, setupComplete: true, executorMode: draft.mode, mysqlMode, model: draft.model });
    onDone({ login });
  }

  // Enter the LLM flow at the provider picker with a fresh draft carrying the chosen executor.
  // A provider with no preset base_url (the custom OpenAI-compatible endpoint) is routed to the
  // Base-URL prompt first; firstLlmStep encodes the branch (see providers.ts).
  function afterProvider(id: string): void {
    const p = getProvider(id)!;
    set({ providerId: id, base_url: p.baseUrl, auth_mode: p.authModes[0] });
    setStep(firstLlmStep(p));
  }

  // After a model is chosen: Anthropic → pick a thinking level; others → finalize.
  function afterModel(model: string): void {
    if (getProvider(d.providerId)?.kind === 'anthropic') {
      set({ model });
      setStep('thinking');
    } else {
      finalize({ ...d, model });
    }
  }

  // Fetch the catalog when we reach model_fetch; branch to picker or manual entry.
  useEffect(() => {
    if (step !== 'model_fetch') return;
    const p = getProvider(d.providerId)!;
    let alive = true;
    const cred = d.auth_mode === 'oauth' ? d.auth_token : d.api_key; // oauth bearer vs api key
    // Every provider (custom included) picks from the live catalog; a failed fetch lands on the
    // error screen (retry / re-enter), never a silent hand-typed-model prompt.
    const onEmpty: Step = 'model_error';
    fetchModels(p, { baseUrl: d.base_url, apiKey: cred, authMode: d.auth_mode })
      .then((list) => {
        if (!alive) return;
        setModels(list);
        setStep(list.length > 0 ? 'model_pick' : onEmpty);
      })
      .catch(() => alive && setStep(onEmpty));
    return () => {
      alive = false;
    };
  }, [step]);

  return (
    <Box flexDirection="column">
      <Text color="yellow">{llmOnly ? 'configure LLM provider' : 'first-time setup'}</Text>

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

      {step === 'base_url' && (
        // Custom OpenAI-compatible endpoint: capture the Base URL (vLLM, LM Studio, …) so the
        // model catalog can be fetched from `${base_url}/models` — no hand-typed model id needed.
        <TextField
          key="base_url"
          label="Base URL (OpenAI-compatible endpoint, e.g. http://localhost:1234/v1):"
          initial={d.base_url}
          onSubmit={(v) => {
            const base = v.trim().replace(/\/+$/, '');
            set({ base_url: base });
            setStep(stepAfterBaseUrl(getProvider(d.providerId)!));
          }}
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
            else if (m === 'oauth') finalize({ ...d, auth_mode: m, model: '' }); // /login next: opens browser, fetches models, picks
            else setStep('model_fetch'); // none = local, no key
          }}
        />
      )}

      {step === 'api_key' && (
        <TextField key="api_key" label={`${getProvider(d.providerId)?.label} API key (blank if none):`} mask
          onSubmit={(v) => {
            // The OpenAI client throws on an empty api_key, so a local no-auth custom server gets a
            // harmless placeholder (servers that don't check auth ignore it).
            const key = v.trim() || (d.providerId === CUSTOM_PROVIDER ? 'sk-noauth' : v);
            set({ api_key: key });
            setStep('model_fetch');
          }} />
      )}

      {step === 'model_fetch' && (
        <Text color="gray">fetching {getProvider(d.providerId)?.label} models…</Text>
      )}

      {step === 'model_pick' && (
        <FilterSelect
          title={`pick a model (${getProvider(d.providerId)?.label})`}
          items={models.map((m) => ({ label: m, value: m }))}
          onSelect={afterModel}
          onCancel={() => setStep('model_error')}
        />
      )}

      {step === 'model_manual' && (
        // Custom endpoint only — named providers never reach here.
        <TextField
          key="model"
          label={`Model name (e.g. ${getProvider(d.providerId)?.modelHint ?? 'model-id'}):`}
          initial={d.model}
          onSubmit={afterModel}
        />
      )}

      {step === 'model_error' && (
        <Box flexDirection="column">
          <Text color="red">
            couldn't fetch {getProvider(d.providerId)?.label} models — check the Base URL / API key / connectivity.
          </Text>
          <Select<string>
            label="what now?"
            items={[
              { label: 'Retry fetch', value: 'retry' },
              // Custom endpoint: the Base URL is user-supplied, so allow correcting it here.
              ...(d.providerId === CUSTOM_PROVIDER ? [{ label: 'Re-enter Base URL', value: 'base_url' }] : []),
              { label: 'Re-enter API key', value: 'key' },
              // Last-resort escape hatch for a server with no /models endpoint (not the default path).
              { label: 'Enter model id manually', value: 'manual' },
              { label: 'Back to provider list', value: 'provider' },
            ]}
            onSelect={(v) =>
              setStep(
                v === 'retry' ? 'model_fetch'
                  : v === 'base_url' ? 'base_url'
                  : v === 'key' ? 'api_key'
                  : v === 'manual' ? 'model_manual'
                  : 'provider',
              )
            }
          />
        </Box>
      )}

      {step === 'thinking' && (
        <Select<string>
          label="Extended-thinking level (Claude):"
          items={THINKING_LEVELS.map((t) => ({ label: t.label, value: t.id }))}
          onSelect={(lvl) => finalize({ ...d, thinking_level: lvl })}
        />
      )}

      {step === 'mysql' && (
        <Select<MysqlMode>
          label="Where does MySQL run? (sessions/plans/tasks store)"
          items={[
            { label: 'Docker container (octopus starts + manages it) — recommended', value: 'docker' },
            { label: 'Local install (you run MySQL yourself on 127.0.0.1:3306)', value: 'local' },
          ]}
          onSelect={(mode) => commit(d, mode)}
        />
      )}
    </Box>
  );
}
