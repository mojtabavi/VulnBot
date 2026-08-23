import asyncio
import re
import time

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
from rag.kb.api.kb_doc_api import search_docs
from rag.reranker.reranker import LangchainReranker
from server.utils.utils import LLMType, replace_ip_with_targetip
from utils.log_common import build_logger

logger = build_logger()


class OpenAIChat(ABC):
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url, timeout=config.timeout)
        self.model_name = self.config.llm_model_name

    @retry(
        stop=stop_after_attempt(3),  # Stop after 3 attempts
    )
    def chat(self, history: List) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=history,
                temperature=self.config.temperature,
            )
            ans = response.choices[0].message.content
            return ans
        except (httpx.HTTPStatusError, httpx.ReadTimeout,
                    httpx.ConnectTimeout, ConnectionError) as e:
            if getattr(e, "response", None) and e.response.status_code == 429:
                # Rate limit error, wait longer
                time.sleep(2)
            raise  # Re-raise the exception to trigger retry
        except Exception as e:
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

    @retry(
        stop=stop_after_attempt(3),
    )
    def chat(self, history: List[dict]) -> str:
        try:
            system, msgs = self._split_history(history)
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=getattr(self.config, "max_tokens", 4096),
                temperature=self.config.temperature,
                system=system,
                messages=msgs,
            )
            # content is a list of blocks; concatenate the text blocks.
            return "".join(getattr(block, "text", "") for block in response.content)
        except (httpx.HTTPStatusError, httpx.ReadTimeout,
                    httpx.ConnectTimeout, ConnectionError) as e:
            if getattr(e, "response", None) and e.response.status_code == 429:
                time.sleep(2)
            raise
        except Exception as e:
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
