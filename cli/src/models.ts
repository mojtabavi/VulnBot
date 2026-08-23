/** Live model-catalog fetch. Uses Node's global fetch (Node 18+) — NO new dependency.
 *  Never throws: any error (offline, 401, timeout, bad JSON) resolves to [] so the wizard
 *  falls back to manual model entry. Short timeout so an unreachable endpoint can't hang. */
import type { Provider, AuthMode } from './providers.js';
import { modelsUrlFor } from './providers.js';

const DEFAULT_TIMEOUT_MS = 6000;

export interface FetchModelsOpts {
  /** override the provider's preset base_url (custom / self-hosted) */
  baseUrl?: string;
  /** API key or OAuth bearer token, depending on authMode */
  apiKey?: string;
  authMode?: AuthMode;
  timeoutMs?: number;
  /** injectable for offline unit tests; defaults to global fetch */
  fetchImpl?: typeof fetch;
}

/** Build auth + shape-specific headers for a provider's /models GET. */
function headersFor(p: Provider, apiKey?: string, authMode: AuthMode = 'api_key'): Record<string, string> {
  const h: Record<string, string> = { Accept: 'application/json' };
  if (p.kind === 'anthropic') {
    // Native Anthropic /v1/models. api_key → x-api-key; oauth (Pro/Max) → bearer + beta.
    h['anthropic-version'] = '2023-06-01';
    if (authMode === 'oauth' && apiKey) {
      h['Authorization'] = `Bearer ${apiKey}`;
      h['anthropic-beta'] = 'oauth-2025-04-20';
    } else if (apiKey) {
      h['x-api-key'] = apiKey;
    }
    return h;
  }
  // OpenAI-wire (openai/qwen/kimi/deepseek/openrouter/custom) + ollama: standard bearer.
  if (apiKey) h['Authorization'] = `Bearer ${apiKey}`;
  return h;
}

/** Parse a models payload into a sorted, de-duplicated id list across known shapes. */
function parseModels(data: any): string[] {
  let ids: string[] = [];
  if (data && Array.isArray(data.data)) {
    // OpenAI shape (also OpenRouter, Anthropic native): { data: [{ id }] }
    ids = data.data.map((m: any) => m?.id).filter(Boolean);
  } else if (data && Array.isArray(data.models)) {
    // Ollama shape: { models: [{ name }] }
    ids = data.models.map((m: any) => m?.name ?? m?.model).filter(Boolean);
  } else if (Array.isArray(data)) {
    ids = data.map((m: any) => (typeof m === 'string' ? m : m?.id ?? m?.name)).filter(Boolean);
  }
  return Array.from(new Set(ids)).sort();
}

/** Fetch the provider's model catalog. Resolves to a (possibly empty) id list; never rejects. */
export async function fetchModels(p: Provider, opts: FetchModelsOpts = {}): Promise<string[]> {
  const url = modelsUrlFor(p, opts.baseUrl);
  if (!url) return []; // no catalog endpoint (bare custom base) → manual entry
  const doFetch = opts.fetchImpl ?? globalThis.fetch;
  if (!doFetch) return [];

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  try {
    const res = await doFetch(url, {
      method: 'GET',
      headers: headersFor(p, opts.apiKey, opts.authMode ?? p.authModes[0]),
      signal: ctrl.signal,
    });
    if (!res.ok) return [];
    const data = await res.json();
    return parseModels(data);
  } catch {
    return []; // offline / abort / bad JSON — caller handles empty as "type it manually"
  } finally {
    clearTimeout(timer);
  }
}
