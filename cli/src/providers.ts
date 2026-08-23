/** Provider registry: presets for the well-known LLM providers the wizard can target.
 *  Endpoints only — NO secrets. Keys/tokens live in model_config.yaml / .env at runtime.
 *
 *  `kind` is the Python client dispatched in server/chat/chat.py::_chat:
 *    - 'openai'    → OpenAIChat (OpenAI-wire-compatible: OpenAI/Qwen/Kimi/DeepSeek/OpenRouter)
 *    - 'anthropic' → native AnthropicChat (added in B5; carries the OAuth subscription token)
 *    - 'ollama'    → OllamaChat (local, no key, no /models catalog)
 *
 *  Most hosted providers share the OpenAI wire format, so they reuse the existing
 *  OpenAIChat wrapper and differ only by baseUrl / modelsUrl / model id. */

export type ProviderKind = 'openai' | 'anthropic' | 'ollama';
export type AuthMode = 'api_key' | 'oauth' | 'none';

export interface Provider {
  /** stable id written to model_config.yaml as `llm_provider` */
  id: string;
  /** human label for the wizard list */
  label: string;
  /** Python client kind (`llm_model` in model_config.yaml) */
  kind: ProviderKind;
  /** OpenAI-compatible base_url (empty = user must supply, e.g. generic/ollama) */
  baseUrl: string;
  /** GET endpoint returning the model catalog (empty = no live fetch → manual entry) */
  modelsUrl: string;
  /** supported auth modes, first = default */
  authModes: AuthMode[];
  /** optional extra HTTP headers (e.g. OpenRouter ranking headers; values may be empty presets) */
  headers?: Record<string, string>;
  /** docs link surfaced in the wizard */
  docs: string;
  /** hint shown when asking for the model id manually */
  modelHint?: string;
}

/** Ordered registry — order drives the wizard Select list. */
export const PROVIDERS: Provider[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    kind: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    modelsUrl: 'https://api.openai.com/v1/models',
    authModes: ['api_key'],
    docs: 'https://platform.openai.com/docs/models',
    modelHint: 'gpt-4o',
  },
  {
    id: 'anthropic',
    label: 'Anthropic (Claude — native)',
    kind: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    modelsUrl: 'https://api.anthropic.com/v1/models',
    authModes: ['api_key', 'oauth'], // oauth = Claude Pro/Max subscription (B6)
    docs: 'https://docs.anthropic.com/en/docs/about-claude/models',
    modelHint: 'claude-sonnet-4-5',
  },
  {
    id: 'anthropic-compat',
    label: 'Anthropic (Claude — OpenAI-compat)',
    kind: 'openai',
    baseUrl: 'https://api.anthropic.com/v1',
    modelsUrl: 'https://api.anthropic.com/v1/models',
    authModes: ['api_key'],
    docs: 'https://docs.anthropic.com/en/api/openai-sdk',
    modelHint: 'claude-sonnet-4-5',
  },
  {
    id: 'qwen',
    label: 'Qwen (DashScope)',
    kind: 'openai',
    baseUrl: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
    modelsUrl: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models',
    authModes: ['api_key'],
    docs: 'https://www.alibabacloud.com/help/en/model-studio/',
    modelHint: 'qwen-plus',
  },
  {
    id: 'kimi',
    label: 'Kimi (Moonshot)',
    kind: 'openai',
    baseUrl: 'https://api.moonshot.ai/v1',
    modelsUrl: 'https://api.moonshot.ai/v1/models',
    authModes: ['api_key'],
    docs: 'https://platform.moonshot.ai/docs',
    modelHint: 'kimi-k2-0905-preview',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    kind: 'openai',
    baseUrl: 'https://api.deepseek.com/v1',
    modelsUrl: 'https://api.deepseek.com/v1/models',
    authModes: ['api_key'],
    docs: 'https://api-docs.deepseek.com/',
    modelHint: 'deepseek-chat',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter (300+ models)',
    kind: 'openai',
    baseUrl: 'https://openrouter.ai/api/v1',
    modelsUrl: 'https://openrouter.ai/api/v1/models',
    authModes: ['api_key'],
    // Optional ranking headers — empty presets, safe to leave blank.
    headers: { 'HTTP-Referer': '', 'X-Title': '' },
    docs: 'https://openrouter.ai/docs',
    modelHint: 'anthropic/claude-sonnet-4.5',
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    kind: 'ollama',
    baseUrl: 'http://localhost:11434',
    modelsUrl: 'http://localhost:11434/api/tags', // ollama-native shape (not /v1/models)
    authModes: ['none'],
    docs: 'https://ollama.com/library',
    modelHint: 'llama3.1',
  },
  {
    id: 'openai-compatible',
    label: 'Custom (OpenAI-compatible)',
    kind: 'openai',
    baseUrl: '', // user supplies (vLLM, LM Studio, etc.)
    modelsUrl: '', // derived as `${baseUrl}/models` at fetch time when non-empty
    authModes: ['api_key'], // just a key; blank on a local no-auth server is placeholdered in Setup
    docs: '',
    modelHint: 'your-model-id',
  },
];

/** Extended-thinking levels (Anthropic only). `budget` = thinking token budget; 0 = disabled.
 *  The Python AnthropicChat maps `budget` → messages.create(thinking={type:enabled,budget_tokens}). */
export interface ThinkingLevel {
  id: string;
  label: string;
  budget: number;
}
export const THINKING_LEVELS: ThinkingLevel[] = [
  { id: 'off', label: 'Off (no extended thinking)', budget: 0 },
  { id: 'low', label: 'Low (~4k thinking tokens)', budget: 4000 },
  { id: 'medium', label: 'Medium (~12k thinking tokens)', budget: 12000 },
  { id: 'high', label: 'High (~24k thinking tokens)', budget: 24000 },
];

/** Setup-wizard step ids the LLM sub-flow routes through (see cli/src/ui/Setup.tsx). */
export type LlmStep = 'base_url' | 'auth' | 'api_key' | 'model_fetch';

/** First wizard step after a provider is chosen. A provider with no preset baseUrl (the custom
 *  OpenAI-compatible endpoint) must supply a Base URL first; the rest branch on auth. */
export function firstLlmStep(p: Provider): LlmStep {
  if (!p.baseUrl) return 'base_url';
  return stepAfterBaseUrl(p);
}

/** Step once base_url is known: multi-auth → pick a mode; keyless (ollama) → fetch; else → API key. */
export function stepAfterBaseUrl(p: Provider): Exclude<LlmStep, 'base_url'> {
  if (p.authModes.length > 1) return 'auth';
  if (p.authModes[0] === 'none') return 'model_fetch';
  return 'api_key';
}

const BY_ID = new Map(PROVIDERS.map((p) => [p.id, p]));

export function getProvider(id: string): Provider | undefined {
  return BY_ID.get(id);
}

export function listProviders(): Provider[] {
  return PROVIDERS;
}

/** The /models URL for a provider, resolving the generic case from a supplied base_url. */
export function modelsUrlFor(p: Provider, baseUrl?: string): string {
  if (p.modelsUrl) return p.modelsUrl;
  const b = (baseUrl ?? p.baseUrl).replace(/\/+$/, '');
  return b ? `${b}/models` : '';
}
