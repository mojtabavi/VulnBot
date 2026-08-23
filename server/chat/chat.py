import asyncio
import re
import sys

import httpx
from typing import List, Optional
from abc import ABC
from openai import OpenAI
from ollama import Client
from starlette.concurrency import run_in_threadpool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.config import Configs
from db.repository.conversation_repository import add_conversation_to_db
from db.repository.message_repository import get_conversation_messages, add_message_to_db
# NOTE: rag.* pulls in langchain (heavy). It is only needed when enable_rag is on, so the imports
# are deferred into the RAG branch of _chat — the pentest pipeline runs with enable_rag: false and
# must not require the RAG/ML stack just to import this module.
from server.utils.utils import LLMType, replace_ip_with_targetip
from utils.log_common import build_logger
from utils.progress import emit

logger = build_logger()


# ── transient-API waiting notifier (503 overloaded / 5xx / rate-limit retries) ──────────
# When the LLM endpoint flaps (503 overloaded, 5xx, timeout, 429), the client retries with
# exponential backoff instead of failing the call. These hooks stream an `llm` progress
# marker so the octopus CLI shows a live "waiting for LLM response…" indicator during the
# backoff — a flaky/overloaded API reads as a wait, not a frozen run. Best-effort: an emit
# failure must never affect the run.
_llm_waited = False


def _status_of(exc) -> str:
    """Human-ish status tag for a failed API call (HTTP code if we have one, else class name)."""
    code = getattr(exc, "status_code", None)
    if not code and getattr(exc, "response", None) is not None:
        code = getattr(exc.response, "status_code", None)
    if code:
        return str(code)
    return {
        "OverloadedError": "503", "RateLimitError": "429", "InternalServerError": "500",
        "APITimeoutError": "timeout", "APIConnectionError": "connection",
        "ReadTimeout": "timeout", "ConnectTimeout": "timeout",
    }.get(type(exc).__name__, type(exc).__name__)


def _notify_llm_wait(retry_state) -> None:
    """tenacity before_sleep hook: announce we're waiting on the API + will retry after backoff."""
    global _llm_waited
    _llm_waited = True
    try:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        status = _status_of(exc) if exc is not None else "?"
        wait = getattr(getattr(retry_state, "next_action", None), "sleep", 0) or 0
        emit("llm", state="waiting", attempt=retry_state.attempt_number, status=status, wait=f"{wait:.0f}")
        logger.warning(f"LLM {status} - waiting {wait:.0f}s then retry (attempt {retry_state.attempt_number})")
    except Exception:
        pass


def _notify_llm_ok() -> None:
    """Announce the API responded after we had been waiting (clears the CLI indicator)."""
    global _llm_waited
    if _llm_waited:
        _llm_waited = False
        try:
            emit("llm", state="ok")
        except Exception:
            pass


# HTTP status codes worth retrying with backoff: rate limit (429), overloaded (503/529), 5xx.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504, 529}
# APIStatusError subclass names (openai + anthropic SDKs) that mean "transient — retry".
_RETRYABLE_NAMES = {
    "RateLimitError", "InternalServerError", "OverloadedError",
    "APITimeoutError", "APIConnectionError", "APIConnectionTimeoutError",
}


def _is_retryable(exc) -> bool:
    """True for transient API failures (503 overloaded, 5xx, timeouts, rate limit)."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)
    if not status and getattr(exc, "response", None) is not None:
        status = getattr(exc.response, "status_code", None)
    return status in _RETRYABLE_STATUS or type(exc).__name__ in _RETRYABLE_NAMES


def _anthropic_has_thinking() -> bool:
    """True iff the installed anthropic SDK understands the extended-thinking `thinking=` param
    (added in 0.47). Older SDKs (e.g. the previously-pinned 0.40) raise
    `TypeError: Messages.create() got an unexpected keyword argument 'thinking'` — and can't model
    the thinking response blocks either — so we degrade to a normal call. Fail safe to False."""
    try:
        import anthropic
        parts = str(anthropic.__version__).split(".")
        major, minor = int(parts[0]), int(parts[1])
        return (major, minor) >= (0, 47)
    except Exception:
        return False


_ANTHROPIC_HAS_THINKING = _anthropic_has_thinking()
_THINKING_UNSUPPORTED_WARNED = False

# ── adaptive thinking (rate-limit avoidance) ──────────────────────────────────────────
# On a 429 the extended-thinking budget is stepped DOWN process-wide so subsequent calls are lighter
# and stop tripping the limit. Runtime-only (no config write): resets next process. off < low < ....
THINKING_ORDER = ("off", "low", "medium", "high")
_thinking_cap = None  # None = uncapped; else the highest thinking level currently allowed


def _thinking_rank(level: str) -> int:
    try:
        return THINKING_ORDER.index(level)
    except ValueError:
        return 0


def _effective_thinking(level: str) -> str:
    """The configured level, capped by any downgrade forced by a prior rate limit."""
    if _thinking_cap is None:
        return level
    return THINKING_ORDER[min(_thinking_rank(level), _thinking_rank(_thinking_cap))]


def _downgrade_thinking(current: str) -> None:
    """Lower the process-wide cap to one step below `current` (floor 'off') after a 429, and announce
    it once. The `**RATE-LIMIT**` line is a SOFT notice the octopus CLI surfaces as a ⚠ warning."""
    global _thinking_cap
    new_rank = max(0, _thinking_rank(current) - 1)
    new_level = THINKING_ORDER[new_rank]
    if _thinking_cap is not None and _thinking_rank(_thinking_cap) <= new_rank:
        return  # already capped this low or lower
    _thinking_cap = new_level
    sys.stdout.write(f"**RATE-LIMIT**: reduced thinking {current}->{new_level} to avoid rate limiting\n")
    sys.stdout.flush()
    logger.warning(f"rate limited - reduced extended thinking {current} -> {new_level}")


class OpenAIChat(ABC):
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url, timeout=config.timeout)
        self.model_name = self.config.llm_model_name

    # Retry transient API failures (rate limit + 5xx incl. 503 overloaded + timeouts) with
    # exponential backoff, and surface the wait to the CLI via before_sleep — so a flapping or
    # overloaded endpoint recovers instead of poisoning planning with the **ERROR** sentinel.
    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        before_sleep=_notify_llm_wait,
        reraise=True,
    )
    def chat(self, history: List) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=history,
                temperature=self.config.temperature,
            )
            _notify_llm_ok()  # clears the "waiting for LLM" indicator if we had been retrying
            return response.choices[0].message.content
        except Exception as e:
            if _is_retryable(e):
                raise  # → @retry backs off (before_sleep streams the wait to the CLI)
            return f"**ERROR**: {str(e)}"


class AnthropicChat(ABC):
    """Native Anthropic (Claude) client. Two auth modes:
      - api_key: Anthropic(api_key=...) → sends x-api-key.
      - oauth:   Anthropic(api_key=None, auth_token=<subscription bearer>) → sends
                 Authorization: Bearer, plus the anthropic-beta OAuth header.
    base_url must NOT include /v1 (the SDK appends /v1/messages itself).
    The OpenAI-style `history` (system + alternating user/assistant + final user) is mapped
    to Anthropic's shape: the system message becomes the `system` param, the rest stay as
    messages. Imported lazily so non-Anthropic runs don't need the `anthropic` package."""

    # Beta header that authorizes a Pro/Max OAuth token for the Messages API.
    OAUTH_BETA = "oauth-2025-04-20"

    # Extended-thinking level id → thinking token budget. MUST match cli/src/providers.ts
    # THINKING_LEVELS. 0 = disabled.
    THINKING_BUDGETS = {"off": 0, "low": 4000, "medium": 12000, "high": 24000}
    # Extra output tokens reserved above the thinking budget (max_tokens must exceed budget).
    THINKING_OUTPUT_ALLOWANCE = 8192

    def __init__(self, config):
        from anthropic import Anthropic  # lazy: only needed when llm_model == anthropic

        self.config = config
        self.model_name = config.llm_model_name
        base_url = config.base_url or "https://api.anthropic.com"
        if getattr(config, "auth_mode", "api_key") == "oauth":
            self.client = Anthropic(
                api_key=None,
                auth_token=config.auth_token,
                base_url=base_url,
                timeout=config.timeout,
                default_headers={"anthropic-beta": self.OAUTH_BETA},
            )
        else:
            self.client = Anthropic(api_key=config.api_key, base_url=base_url, timeout=config.timeout)

    @staticmethod
    def _split_history(history: List[dict]):
        """→ (system_prompt, messages) with the system entry pulled out of the list."""
        system = "You are a helpful assistant"
        msgs = []
        for m in history:
            if m.get("role") == "system":
                system = m.get("content", system)
            else:
                msgs.append({"role": m["role"], "content": m["content"]})
        return system, msgs

    def _create(self, kwargs: dict):
        """messages.create with a self-healing retry for models that reject `temperature`.
        Newer Claude models (e.g. claude-opus-4-x) return `400 temperature is deprecated for this
        model`; drop the offending param and retry once rather than failing the whole call."""
        try:
            return self.client.messages.create(**kwargs)
        except Exception as e:
            if (getattr(e, "status_code", None) == 400 and "temperature" in str(e).lower()
                    and "temperature" in kwargs):
                kwargs.pop("temperature", None)
                return self.client.messages.create(**kwargs)
            raise

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        before_sleep=_notify_llm_wait,  # stream a "waiting for LLM response…" indicator to the CLI
        reraise=True,
    )
    def chat(self, history: List[dict]) -> str:
        try:
            system, msgs = self._split_history(history)
            max_tokens = getattr(self.config, "max_tokens", 4096)
            # Effective level = configured, capped by any downgrade a prior 429 forced (rate-limit
            # avoidance). A new AnthropicChat is built per _chat call, so the module-level cap is what
            # carries the reduced level across the whole run.
            self._effective_level = _effective_thinking(getattr(self.config, "thinking_level", "off"))
            budget = self.THINKING_BUDGETS.get(self._effective_level, 0)
            kwargs = dict(model=self.model_name, system=system, messages=msgs)
            if budget > 0 and _ANTHROPIC_HAS_THINKING:
                # Extended thinking: budget must be < max_tokens, and the API requires
                # temperature == 1 while thinking is enabled.
                kwargs["max_tokens"] = max(max_tokens, budget + self.THINKING_OUTPUT_ALLOWANCE)
                kwargs["temperature"] = 1
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
            else:
                if budget > 0:
                    # Thinking requested but the installed SDK is too old — degrade to a plain call
                    # (warn once) instead of passing a kwarg it rejects and poisoning planning.
                    global _THINKING_UNSUPPORTED_WARNED
                    if not _THINKING_UNSUPPORTED_WARNED:
                        logger.warning("anthropic SDK <0.47 - extended thinking disabled; "
                                       "upgrade (pip install -U anthropic) to enable")
                        _THINKING_UNSUPPORTED_WARNED = True
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = self.config.temperature
            response = self._create(kwargs)
            _notify_llm_ok()  # clears the "waiting for LLM" indicator if we had been retrying
            # content is a list of blocks; concatenate the text blocks (thinking blocks have no .text).
            return "".join(getattr(block, "text", "") for block in response.content)
        except Exception as e:
            # The modern anthropic SDK raises APIStatusError subclasses (RateLimitError=429,
            # InternalServerError=5xx, OverloadedError=503/529), NOT httpx errors — re-raise the
            # retryable ones so @retry backs off (before_sleep streams the wait to the CLI) instead
            # of swallowing them into the "**ERROR**" sentinel (which then poisons planning).
            status = getattr(e, "status_code", None)
            is_rate_limit = status == 429 or type(e).__name__ == "RateLimitError"
            if is_rate_limit:
                # Step thinking down before the retry so the next attempt is lighter on tokens and
                # stops tripping the limit (the #1 cause on the OAuth-subscription path).
                _downgrade_thinking(getattr(self, "_effective_level", "off"))
            if _is_retryable(e):
                raise
            return f"**ERROR**: {str(e)}"


class OllamaChat(ABC):
    def __init__(self, config):
        self.config = config
        self.client = Client(host=self.config.base_url)
        self.model_name = self.config.llm_model_name

    def chat(self, history: List[dict]) -> str:

        try:
            options = {
                "temperature": self.config.temperature,
            }
            response = self.client.chat(
                model=self.model_name,
                messages=history,
                options=options,
                keep_alive=-1
            )
            ans = response["message"]["content"]
            return ans
        except httpx.HTTPStatusError as e:
            return f"**ERROR**: {str(e)}"


def _chat(query: str, kb_name=None, conversation_id=None, kb_query=None, summary=True):
    try:
        if Configs.basic_config.enable_rag and kb_name is not None:
            # Deferred here so importing chat.py doesn't require langchain when RAG is off.
            from rag.kb.api.kb_doc_api import search_docs
            from rag.reranker.reranker import LangchainReranker

            docs = asyncio.run(run_in_threadpool(search_docs,
                                                 query=kb_query,
                                                 knowledge_base_name=kb_name,
                                                 top_k=Configs.kb_config.top_k,
                                                 score_threshold=Configs.kb_config.score_threshold,
                                                 file_name="",
                                                 metadata={}))

            reranker_model = LangchainReranker(top_n=Configs.kb_config.top_n,
                                               name_or_path=Configs.llm_config.rerank_model)

            docs = reranker_model.compress_documents(documents=docs, query=kb_query)

            if len(docs) == 0:
                context = ""
            else:
                context = "\n".join([doc["page_content"] for doc in docs])

            if context:
                context = replace_ip_with_targetip(context)
                query = f"{query}\n\n\n Ensure that the **Overall Target** IP or the IP from the **Initial Description** is prioritized. You will respond to questions and generate tasks based on the provided penetration test case materials: {context}. \n"

        if conversation_id is not None and len(query) > 10000:
            query = query[:10000]
        else:
            query = query[:Configs.llm_config.context_length]

        flag = False

        if conversation_id is not None:
            flag = True

        # Initialize or retrieve conversation ID
        conversation_id = add_conversation_to_db(Configs.llm_config.llm_model_name, conversation_id)

        history = [
            {
                "role": "system",
                "content": "You are a helpful assistant",
            }
        ]
        # Retrieve message history from database, and limit the number of messages
        for msg in get_conversation_messages(conversation_id)[-Configs.llm_config.history_len:]:
            history.append({"role": "user", "content": msg.query})
            history.append({"role": "assistant", "content": msg.response})

        # Add user query to the message history
        history.append({"role": "user", "content": query})

        # Initialize the correct model client
        if Configs.llm_config.llm_model == LLMType.OPENAI:
            client = OpenAIChat(config=Configs.llm_config)
        elif Configs.llm_config.llm_model == LLMType.OLLAMA:
            client = OllamaChat(config=Configs.llm_config)
        elif Configs.llm_config.llm_model == LLMType.ANTHROPIC:
            client = AnthropicChat(config=Configs.llm_config)
        else:
            return "Unsupported model type"

        # Get response from the model
        response_text = client.chat(history)

        # Save both query and response to the database
        if summary:
            add_message_to_db(conversation_id, Configs.llm_config.llm_model_name, query, response_text)

        if flag:
            return response_text
        else:
            return response_text, conversation_id

    except Exception as e:
        print(e)
        return f"**ERROR**: {str(e)}"
