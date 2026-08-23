/** Slash-command handler for the REPL. Returns lines to print and an optional UI action. */
import { getModel, setModel, loadPrefs, getModelConfig, setProvider } from './config.js';
import { getProvider, listProviders } from './providers.js';
import { labUp, labDown, labStatus, smoke, dockerAvailable } from './executor.js';
import { formatBelief } from './belief.js';

export interface CommandSpec {
  name: string;
  args: string;
  help: string;
}

/** Command catalog — powers /help and the slash menu/autocomplete. */
export const COMMANDS: CommandSpec[] = [
  { name: 'help', args: '', help: 'show this help' },
  { name: 'setup', args: '', help: 're-run the first-time setup wizard' },
  { name: 'provider', args: '[id]', help: 'switch LLM provider (no arg = picker)' },
  { name: 'model', args: '[name]', help: 'pick/switch the active LLM model (no arg = live picker)' },
  { name: 'login', args: '', help: 'Claude Pro/Max subscription sign-in (OAuth)' },
  { name: 'status', args: '', help: 'provider, auth, model, executor, lab status' },
  { name: 'lab', args: 'up|down|smoke', help: 'control / test the Docker lab' },
  { name: 'belief', args: '[run]', help: 'show the latest belief trace' },
  { name: 'run', args: '[target]', help: 'start an assessment (interim: validates channel)' },
  { name: 'clear', args: '', help: 'clear the screen' },
  { name: 'quit', args: '', help: 'exit' },
];

export interface CommandResult {
  lines: string[];
  action?: 'quit' | 'setup' | 'clear' | 'pick-model' | 'pick-provider' | 'login';
}

/** Whether a command is slow (async work → show a spinner) and its verb label. */
export function commandMeta(input: string): { slow: boolean; label: string } {
  const [cmd, sub] = input.trim().replace(/^\//, '').split(/\s+/);
  if (cmd === 'lab' && sub === 'up') return { slow: true, label: 'Starting lab…' };
  if (cmd === 'lab' && sub === 'down') return { slow: true, label: 'Stopping lab…' };
  if (cmd === 'lab' && sub === 'smoke') return { slow: true, label: 'Scanning target…' };
  if (cmd === 'lab') return { slow: true, label: 'Working on lab…' };
  if (cmd === 'run') return { slow: true, label: 'Processing…' };
  if (cmd === 'status') return { slow: true, label: 'Checking status…' };
  return { slow: false, label: 'Working…' };
}

/** Label the REPL shows while it fetches a model catalog for an overlay picker. */
export function fetchingLabel(): string {
  return `Fetching ${getProvider(getModelConfig().provider)?.label ?? 'provider'} models…`;
}

export async function handleCommand(input: string): Promise<CommandResult> {
  const line = input.trim();
  if (line === '') return { lines: [] };
  if (!line.startsWith('/')) {
    return { lines: [`unrecognized input. type /help (or /run ${line} to target it).`] };
  }
  const [cmd, ...args] = line.slice(1).split(/\s+/);

  switch (cmd) {
    case 'help':
      return { lines: ['commands:', ...COMMANDS.map((c) => `  /${c.name} ${c.args}`.padEnd(24) + c.help)] };

    case 'setup':
      return { lines: ['re-running setup...'], action: 'setup' };

    case 'clear':
      return { lines: [], action: 'clear' };

    case 'quit':
    case 'exit':
      return { lines: ['bye.'], action: 'quit' };

    case 'model': {
      // no arg → interactive live picker (Repl fetches the catalog + opens an overlay).
      if (args.length === 0) return { lines: [], action: 'pick-model' };
      setModel(args[0]);
      return { lines: [`model switched -> ${args[0]} (model_config.yaml updated; hot-reloaded on next call)`] };
    }

    case 'provider': {
      // no arg → provider picker overlay; <id> → switch directly.
      if (args.length === 0) return { lines: [], action: 'pick-provider' };
      const id = args[0];
      if (!getProvider(id)) {
        const known = listProviders().map((p) => p.id).join(', ');
        return { lines: [`unknown provider: ${id}`, `known: ${known}`] };
      }
      setProvider(id);
      const p = getProvider(id)!;
      const lines = [`provider -> ${p.label} (base_url ${p.baseUrl || '(custom)'})`];
      if (p.authModes[0] !== 'none') lines.push('set the key with /login (oauth) or re-run /setup; then /model to pick a model.');
      else lines.push('local provider — no key needed; /model to pick a model.');
      return { lines };
    }

    case 'login':
      // Claude Pro/Max OAuth — the flow itself lands in B6; Repl owns the browser step.
      return { lines: [], action: 'login' };

    case 'status': {
      const prefs = loadPrefs();
      const c = getModelConfig();
      const p = getProvider(c.provider);
      const lines = [
        `provider: ${p?.label ?? c.provider}  (${c.kind})`,
        `auth:     ${c.auth_mode === 'oauth' ? 'subscription (Claude Pro/Max)' : c.auth_mode}`,
        `model:    ${c.model || '(unset)'}`,
        `base_url: ${c.base_url || '(unset)'}`,
        `executor: ${prefs.executorMode}`,
      ];
      if (prefs.executorMode === 'docker') lines.push('lab:', ...(await labStatus()).split('\n').map((l) => '  ' + l));
      return { lines };
    }

    case 'lab': {
      const sub = args[0];
      if (!(await dockerAvailable())) return { lines: ['docker not reachable — start Docker Desktop.'] };
      if (sub === 'up') return { lines: [await labUp()] };
      if (sub === 'down') return { lines: [await labDown()] };
      if (sub === 'smoke') return { lines: (await smoke()).split('\n') };
      return { lines: ['usage: /lab up|down|smoke'] };
    }

    case 'belief':
      return { lines: formatBelief(args[0]) };

    case 'run': {
      const target = args[0] ?? '(from setup)';
      const prefs = loadPrefs();
      const lines = [`starting assessment against ${target} via executor=${prefs.executorMode}...`];
      if (prefs.executorMode === 'docker' && (await dockerAvailable())) {
        lines.push(...(await smoke()).split('\n'));
      }
      lines.push(
        'NOTE: the belief-driven pentest episode is wired after belief tasks 2.4/2.5.',
        '      this interim /run validates the executor channel only.'
      );
      return { lines };
    }

    default:
      return { lines: [`unknown command: /${cmd} (try /help)`] };
  }
}
