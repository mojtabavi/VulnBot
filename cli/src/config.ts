/** Config bridge: read/write the project's YAML config + a CLI-only prefs file.
 *  The Python agent reads model_config.yaml / basic_config.yaml, so the wizard writes
 *  those directly (partial writes are fine — pydantic fills the rest from defaults). */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import { PROVIDERS, getProvider, type Provider, type ProviderKind, type AuthMode } from './providers.js';

const here = path.dirname(fileURLToPath(import.meta.url)); // .../cli/src
export const REPO_ROOT = process.env.PENTEST_ROOT
  ? path.resolve(process.env.PENTEST_ROOT)
  : path.resolve(here, '..', '..'); // cli/src -> cli -> repo root

const OCTOPUS_JSON = path.join(here, '..', '.octopus.json'); // cli/.octopus.json

export type ExecutorMode = 'docker' | 'remote' | 'local';
/** Where MySQL runs: 'docker' = the compose `mysql` service (octopus starts it); 'local' = the
 *  user runs their own MySQL. Chosen once at setup, persisted, and used by the /run preflight. */
export type MysqlMode = 'docker' | 'local';

export interface OctopusPrefs {
  setupComplete: boolean;
  executorMode: ExecutorMode;
  mysqlMode?: MysqlMode;
  model?: string;
}

const DEFAULT_PREFS: OctopusPrefs = { setupComplete: false, executorMode: 'docker', mysqlMode: 'docker' };

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
/** What the wizard captures. `provider` = named preset id (llm_provider); `kind` = Python
 *  client dispatched in _chat (llm_model). auth_mode/auth_token carry the Claude subscription. */
export interface ModelSettings {
  provider: string; // named provider id, e.g. 'openrouter' (see providers.ts)
  kind: ProviderKind; // 'openai' | 'anthropic' | 'ollama' — the client
  base_url: string;
  api_key: string;
  model: string;
  auth_mode?: AuthMode; // 'api_key' | 'oauth' | 'none' (default 'api_key')
  auth_token?: string; // OAuth bearer (Claude Pro/Max); git-ignored at rest
  thinking_level?: string; // Anthropic extended-thinking level id ('off'|'low'|'medium'|'high')
}
export function writeModelConfig(m: ModelSettings): void {
  const cfg = loadYaml('model_config.yaml');
  cfg.llm_model = m.kind;
  cfg.llm_provider = m.provider;
  cfg.base_url = m.base_url;
  cfg.api_key = m.api_key;
  cfg.llm_model_name = m.model;
  cfg.auth_mode = m.auth_mode ?? 'api_key';
  cfg.auth_token = m.auth_token ?? '';
  cfg.thinking_level = m.thinking_level ?? 'off';
  dumpYaml('model_config.yaml', cfg);
}
export function getModel(): string {
  return loadYaml('model_config.yaml').llm_model_name ?? '(unset)';
}
/** Current provider id (falls back to inferring from llm_model kind for legacy configs). */
export function getProviderId(): string {
  const cfg = loadYaml('model_config.yaml');
  return cfg.llm_provider ?? cfg.llm_model ?? '(unset)';
}
export function getAuthMode(): AuthMode {
  return (loadYaml('model_config.yaml').auth_mode as AuthMode) ?? 'api_key';
}
/** Full current model config (for the live model-fetch + /status). Legacy configs backfill. */
export function getModelConfig(): ModelSettings {
  const c = loadYaml('model_config.yaml');
  return {
    provider: c.llm_provider ?? c.llm_model ?? 'openai-compatible',
    kind: (c.llm_model as ProviderKind) ?? 'openai',
    base_url: c.base_url ?? '',
    api_key: c.api_key ?? '',
    model: c.llm_model_name ?? '',
    auth_mode: (c.auth_mode as AuthMode) ?? 'api_key',
    auth_token: c.auth_token ?? '',
    thinking_level: c.thinking_level ?? 'off',
  };
}
/** Persist the Anthropic extended-thinking level (level id, honored by the Python backend). */
export function setThinkingLevel(level: string): void {
  const cfg = loadYaml('model_config.yaml');
  cfg.thinking_level = level;
  dumpYaml('model_config.yaml', cfg);
}
/** Persist an OAuth bearer (Claude Pro/Max) + flip auth_mode. Token plumbing filled in B6. */
export function setAuthToken(token: string): void {
  const cfg = loadYaml('model_config.yaml');
  cfg.auth_mode = 'oauth';
  cfg.auth_token = token;
  dumpYaml('model_config.yaml', cfg);
}
/** Registry passthrough so the UI layer imports one config module. */
export function listProviders(): Provider[] {
  return PROVIDERS;
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
/** /provider — repoint base_url/kind/auth to a named preset. When the provider actually
 *  changes, wipe the previous provider's secrets (a qwen key can't auth Anthropic) and reset
 *  auth_mode to the new provider's default; a re-select of the same provider keeps the key. */
export function setProvider(id: string): boolean {
  const p = getProvider(id);
  if (!p) return false;
  const cfg = loadYaml('model_config.yaml');
  const changed = cfg.llm_provider !== p.id;
  cfg.llm_model = p.kind;
  cfg.llm_provider = p.id;
  if (p.baseUrl) cfg.base_url = p.baseUrl;
  if (changed) {
    cfg.api_key = '';
    cfg.auth_token = '';
    cfg.auth_mode = p.authModes[0];
    cfg.llm_model_name = ''; // force re-pick; a model id is provider-specific
  } else {
    cfg.auth_mode = cfg.auth_mode ?? p.authModes[0];
  }
  dumpYaml('model_config.yaml', cfg);
  return true;
}

// ── basic_config.yaml (Kali executor over SSH) ───────────────────────────────
export interface KaliSettings {
  hostname: string;
  port: number;
  username: string;
  password?: string;
  /** SSH private-key path (repo-relative or absolute). Set for the docker lab (key auth); the
   *  Python ShellManager uses it when present, else falls back to password. */
  key_filename?: string;
}
export function writeKaliConfig(k: KaliSettings, mode: ExecutorMode): void {
  const cfg = loadYaml('basic_config.yaml');
  cfg.kali = {
    hostname: k.hostname,
    port: k.port,
    username: k.username,
    password: k.password ?? '',
    key_filename: k.key_filename ?? '',
  };
  if (mode !== 'local') cfg.mode = cfg.mode ?? 'auto';
  dumpYaml('basic_config.yaml', cfg);
}
export function getKali(): KaliSettings | null {
  const k = loadYaml('basic_config.yaml').kali;
  return k
    ? { hostname: k.hostname, port: k.port, username: k.username, password: k.password, key_filename: k.key_filename ?? '' }
    : null;
}

// ── db_config.yaml (MySQL) ───────────────────────────────────────────────────
export interface DbSettings {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
}
/** Defaults match .env.example / the mysql compose service, so the docker path works out of the box. */
export const DEFAULT_DB: DbSettings = {
  host: '127.0.0.1', port: 3306, user: 'octopus', password: 'octopus', database: 'octopus',
};
export function writeDbConfig(db: DbSettings): void {
  const cfg = loadYaml('db_config.yaml');
  cfg.mysql = { host: db.host, port: db.port, user: db.user, password: db.password, database: db.database };
  dumpYaml('db_config.yaml', cfg);
}
/** Current MySQL host/port/etc (backfills from DEFAULT_DB so the /run preflight always has a target). */
export function getDbConfig(): DbSettings {
  const m = loadYaml('db_config.yaml').mysql ?? {};
  return {
    host: m.host || DEFAULT_DB.host,
    port: Number(m.port) || DEFAULT_DB.port,
    user: m.user || DEFAULT_DB.user,
    password: m.password ?? DEFAULT_DB.password,
    database: m.database || DEFAULT_DB.database,
  };
}
