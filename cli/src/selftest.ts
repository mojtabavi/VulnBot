/** Headless self-test (no Ink/TTY): config read/write, /model switch, belief + command handlers. */
import assert from 'node:assert';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'octopus-'));
process.env.PENTEST_ROOT = tmp;

const { writeModelConfig, getModel, setModel } = await import('./config.js');
const { handleCommand } = await import('./commands.js');
const { formatBelief } = await import('./belief.js');

// config write/read + /model switch
writeModelConfig({ provider: 'openai', base_url: 'http://x/v1', api_key: 'k', model: 'm1' });
assert.strictEqual(getModel(), 'm1', 'writeModelConfig/getModel');
assert.ok(fs.existsSync(path.join(tmp, 'model_config.yaml')), 'model_config.yaml written');
setModel('m2');
assert.strictEqual(getModel(), 'm2', 'setModel');

// command handlers
const help = await handleCommand('/help');
assert.ok(help.lines.length > 3, '/help');
const model = await handleCommand('/model');
assert.ok(model.lines[0].includes('m2'), '/model shows current');
const switched = await handleCommand('/model m3');
assert.ok(switched.lines[0].includes('m3') && getModel() === 'm3', '/model <name>');
const quit = await handleCommand('/quit');
assert.strictEqual(quit.action, 'quit', '/quit action');
const bel = await handleCommand('/belief');
assert.ok(bel.lines.length > 0, '/belief');
assert.ok(formatBelief().length > 0, 'formatBelief');

fs.rmSync(tmp, { recursive: true, force: true });
console.log('SELFTEST PASS');
