/** Config bridge: read/write the project's YAML config + a CLI-only prefs file.
 *  The Python agent reads model_config.yaml / basic_config.yaml, so the wizard writes
 *  those directly (partial writes are fine — pydantic fills the rest from defaults). */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const here = path.dirname(fileURLToPath(import.meta.url)); // .../cli/src
export const REPO_ROOT = process.env.PENTEST_ROOT
  ? path.resolve(process.env.PENTEST_ROOT)
  : path.resolve(here, '..', '..'); // cli/src -> cli -> repo root

const OCTOPUS_JSON = path.join(here, '..', '.octopus.json'); // cli/.octopus.json

export type ExecutorMode = 'docker' | 'remote' | 'local';

export interface OctopusPrefs {
  setupComplete: boolean;
  executorMode: ExecutorMode;
  model?: string;
}

const DEFAULT_PREFS: OctopusPrefs = { setupComplete: false, executorMode: 'docker' };

// ── YAML helpers ─────────────────────────────────────────────────────────────
function yamlPath(name: string): string {
  return path.join(REPO_ROOT, name);
}
function loadYaml(name: string): Record<string, any> {
  const p = yamlPath(name);
  if (!fs.existsSync(p)) return {};
  try {
    return (yaml.load(fs.readFileSync(p, 'utf8')) as Record<string, any>) ?? {};
  } catch {
    return {};
  }
}
function dumpYaml(name: string, data: Record<string, any>): void {
  fs.writeFileSync(yamlPath(name), yaml.dump(data, { lineWidth: 100 }), 'utf8');
}

// ── CLI prefs ────────────────────────────────────────────────────────────────
export function loadPrefs(): OctopusPrefs {
  if (!fs.existsSync(OCTOPUS_JSON)) return { ...DEFAULT_PREFS };
  try {
    return { ...DEFAULT_PREFS, ...JSON.parse(fs.readFileSync(OCTOPUS_JSON, 'utf8')) };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}
export function savePrefs(p: OctopusPrefs): void {
  fs.writeFileSync(OCTOPUS_JSON, JSON.stringify(p, null, 2), 'utf8');
}
export function isFirstRun(): boolean {
  return !loadPrefs().setupComplete;
}

// ── model_config.yaml ────────────────────────────────────────────────────────
export interface ModelSettings {
  provider: 'openai' | 'ollama';
  base_url: string;
  api_key: string;
  model: string;
}
export function writeModelConfig(m: ModelSettings): void {
  const cfg = loadYaml('model_config.yaml');
  cfg.llm_model = m.provider;
  cfg.base_url = m.base_url;
  cfg.api_key = m.api_key;
  cfg.llm_model_name = m.model;
  dumpYaml('model_config.yaml', cfg);
}
export function getModel(): string {
  return loadYaml('model_config.yaml').llm_model_name ?? '(unset)';
}
/** /model — switch the active model name (hot-reloaded by the Python side on mtime change). */
export function setModel(name: string): void {
  const cfg = loadYaml('model_config.yaml');
  cfg.llm_model_name = name;
  dumpYaml('model_config.yaml', cfg);
  const prefs = loadPrefs();
  prefs.model = name;
  savePrefs(prefs);
}

// ── basic_config.yaml (Kali executor over SSH) ───────────────────────────────
export interface KaliSettings {
  hostname: string;
  port: number;
  username: string;
  password?: string;
}
export function writeKaliConfig(k: KaliSettings, mode: ExecutorMode): void {
  const cfg = loadYaml('basic_config.yaml');
  cfg.kali = { hostname: k.hostname, port: k.port, username: k.username, password: k.password ?? '' };
  if (mode !== 'local') cfg.mode = cfg.mode ?? 'auto';
  dumpYaml('basic_config.yaml', cfg);
}
export function getKali(): KaliSettings | null {
  const k = loadYaml('basic_config.yaml').kali;
  return k ? { hostname: k.hostname, port: k.port, username: k.username, password: k.password } : null;
}
