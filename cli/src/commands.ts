/** Slash-command handler for the REPL. Returns lines to print and an optional UI action. */
import { getModel, setModel, loadPrefs } from './config.js';
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
  { name: 'model', args: '[name]', help: 'show or switch the active LLM model' },
  { name: 'status', args: '', help: 'executor mode, model, lab status' },
  { name: 'lab', args: 'up|down|smoke', help: 'control / test the Docker lab' },
  { name: 'belief', args: '[run]', help: 'show the latest belief trace' },
  { name: 'run', args: '[target]', help: 'start an assessment (interim: validates channel)' },
  { name: 'clear', args: '', help: 'clear the screen' },
  { name: 'quit', args: '', help: 'exit' },
];

export interface CommandResult {
  lines: string[];
  action?: 'quit' | 'setup' | 'clear';
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
      if (args.length === 0) return { lines: [`model: ${getModel()}   (usage: /model <name>)`] };
      setModel(args[0]);
      return { lines: [`model switched -> ${args[0]} (model_config.yaml updated; hot-reloaded on next call)`] };
    }

    case 'status': {
      const prefs = loadPrefs();
      const lines = [`executor: ${prefs.executorMode}`, `model:    ${getModel()}`];
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
