"""Offline unit test for the native AnthropicChat wrapper (B5).

No live API call: the `anthropic` SDK is replaced with a fake that records constructor
kwargs and returns canned content blocks. The heavy RAG/db imports at the top of
server/chat/chat.py are stubbed so the module imports without the full ML stack.

Asserts:
  - auth_mode 'api_key'  -> Anthropic(api_key=..., no auth_token, no oauth beta header)
  - auth_mode 'oauth'    -> Anthropic(api_key=None, auth_token=..., anthropic-beta header)
  - base_url defaults to https://api.anthropic.com (SDK appends /v1)
  - history is mapped: system message -> `system` param; the rest -> `messages`
  - text content blocks are concatenated into the returned string
"""
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

# ── stub the RAG/db deps chat.py imports at module load (missing without the ML stack) ──
for _name in [
    "rag", "rag.kb", "rag.kb.api", "rag.kb.api.kb_doc_api",
    "rag.reranker", "rag.reranker.reranker",
    "db.repository.conversation_repository", "db.repository.message_repository",
]:
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.modules["rag.kb.api.kb_doc_api"].search_docs = MagicMock()
sys.modules["rag.reranker.reranker"].LangchainReranker = MagicMock()
sys.modules["db.repository.conversation_repository"].add_conversation_to_db = MagicMock()
sys.modules["db.repository.message_repository"].get_conversation_messages = MagicMock()
sys.modules["db.repository.message_repository"].add_message_to_db = MagicMock()

# ── fake anthropic SDK ──────────────────────────────────────────────────────────────
_INITS = []  # constructor kwargs of every fake Anthropic() built


class _FakeMessages:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kwargs):
        self.parent.create_kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text="hello "), SimpleNamespace(text="world")])


class _FakeAnthropic:
    def __init__(self, **kwargs):
        _INITS.append(kwargs)
        self.create_kwargs = None
        self.messages = _FakeMessages(self)


_anthropic_mod = types.ModuleType("anthropic")
_anthropic_mod.Anthropic = _FakeAnthropic
_anthropic_mod.__version__ = "0.49.0"  # modern SDK → extended-thinking capability gate is True
sys.modules["anthropic"] = _anthropic_mod

import server.chat.chat as chat_module  # noqa: E402  (after stubs installed)
from server.chat.chat import AnthropicChat  # noqa: E402


def _cfg(**over):
    base = dict(
        api_key="sk-test",
        auth_mode="api_key",
        auth_token="",
        base_url="",
        timeout=600,
        temperature=0.5,
        llm_model_name="claude-sonnet-4-5",
        max_tokens=1234,
        thinking_level="off",
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_api_key_auth_uses_x_api_key():
    _INITS.clear()
    AnthropicChat(_cfg())
    init = _INITS[-1]
    assert init.get("api_key") == "sk-test"
    assert not init.get("auth_token")  # api-key mode does not send a bearer
    # default base_url when unset (SDK appends /v1, so NO /v1 here)
    assert init.get("base_url") == "https://api.anthropic.com"
    assert "default_headers" not in init  # no oauth beta header


def test_oauth_auth_uses_bearer_and_beta_header():
    _INITS.clear()
    AnthropicChat(_cfg(auth_mode="oauth", auth_token="tok-abc", api_key="sk-ignored"))
    init = _INITS[-1]
    assert init.get("api_key") is None  # no x-api-key under oauth
    assert init.get("auth_token") == "tok-abc"
    assert init["default_headers"]["anthropic-beta"] == AnthropicChat.OAUTH_BETA


def test_custom_base_url_is_preserved():
    _INITS.clear()
    AnthropicChat(_cfg(base_url="https://proxy.internal"))
    assert _INITS[-1].get("base_url") == "https://proxy.internal"


def test_chat_maps_history_and_concatenates_text():
    chat = AnthropicChat(_cfg())
    history = [
        {"role": "system", "content": "SYS PROMPT"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    out = chat.chat(history)
    assert out == "hello world"  # both text blocks concatenated
    kw = chat.client.create_kwargs
    assert kw["system"] == "SYS PROMPT"  # system pulled out of the message list
    assert kw["messages"] == [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    assert kw["max_tokens"] == 1234
    assert kw["model"] == "claude-sonnet-4-5"
    assert "thinking" not in kw  # off → no extended thinking


def test_thinking_level_sets_budget_and_temperature():
    chat = AnthropicChat(_cfg(thinking_level="medium", max_tokens=1234))
    chat.chat([{"role": "user", "content": "hi"}])
    kw = chat.client.create_kwargs
    assert kw["thinking"] == {"type": "enabled", "budget_tokens": 12000}
    assert kw["temperature"] == 1  # API requires temperature 1 while thinking is enabled
    assert kw["max_tokens"] > 12000  # max_tokens must exceed the thinking budget


def test_thinking_off_leaves_temperature_and_max_tokens():
    chat = AnthropicChat(_cfg(thinking_level="off", max_tokens=1234, temperature=0.5))
    chat.chat([{"role": "user", "content": "hi"}])
    kw = chat.client.create_kwargs
    assert "thinking" not in kw
    assert kw["temperature"] == 0.5
    assert kw["max_tokens"] == 1234


def test_effective_thinking_and_downgrade(monkeypatch):
    # A 429 steps the process-wide cap down one level; _effective_thinking honors the cap.
    monkeypatch.setattr(chat_module, "_thinking_cap", None)
    assert chat_module._effective_thinking("high") == "high"       # uncapped
    chat_module._downgrade_thinking("high")
    assert chat_module._thinking_cap == "medium"
    assert chat_module._effective_thinking("high") == "medium"     # capped down
    chat_module._downgrade_thinking("medium")
    assert chat_module._thinking_cap == "low"
    chat_module._downgrade_thinking("low")
    assert chat_module._thinking_cap == "off"
    chat_module._downgrade_thinking("off")                          # floor
    assert chat_module._thinking_cap == "off"


def test_chat_uses_downgraded_thinking(monkeypatch):
    # After a prior 429 forced thinking off, a config of high still sends a plain (no-thinking) call.
    monkeypatch.setattr(chat_module, "_thinking_cap", "off")
    chat = AnthropicChat(_cfg(thinking_level="high", max_tokens=1234, temperature=0.5))
    chat.chat([{"role": "user", "content": "hi"}])
    kw = chat.client.create_kwargs
    assert "thinking" not in kw
    assert kw["temperature"] == 0.5
    assert kw["max_tokens"] == 1234


def test_thinking_degrades_when_sdk_too_old(monkeypatch):
    # Old anthropic SDK (<0.47, e.g. the previously-pinned 0.40) can't accept the `thinking=`
    # kwarg. The gate must degrade to a plain call — never pass thinking — so planning isn't
    # poisoned by the "**ERROR**: ...'thinking'" sentinel.
    monkeypatch.setattr(chat_module, "_ANTHROPIC_HAS_THINKING", False)
    chat = AnthropicChat(_cfg(thinking_level="medium", max_tokens=1234, temperature=0.5))
    chat.chat([{"role": "user", "content": "hi"}])
    kw = chat.client.create_kwargs
    assert "thinking" not in kw
    assert kw["temperature"] == 0.5   # plain call: config temperature, not the thinking-forced 1
    assert kw["max_tokens"] == 1234   # not enlarged for a thinking budget
