"""OpenAI-compatible provider.

Uses the Chat Completions API (NOT the Responses API) because third-party
OpenAI-compatible endpoints (DeepSeek / Kimi / Ollama / etc.) implement Chat
Completions as the de-facto compatibility standard.

Sources:
- Chat Completions streaming:
  https://github.com/openai/openai-python/blob/main/README.md#streaming-responses
- Chat Completions API reference:
  https://platform.openai.com/docs/api-reference/chat/create
  (stream=True yields ChatCompletionChunk objects; delta text is at
   chunk.choices[0].delta.content)
"""
from __future__ import annotations

from typing import Iterator

from openai import OpenAI, APIError, APIConnectionError, AuthenticationError, PermissionDeniedError

from .base import AIProvider, ChatMessage


class AIProviderError(RuntimeError):
    """User-facing error wrapping vendor SDK exceptions."""


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str):
        # timeout kept generous; streaming typically produces first chunk <2s.
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=60.0)

    def stream(self, messages: list[ChatMessage], *, model: str) -> Iterator[str]:
        try:
            resp = self._client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=True,
            )
            for chunk in resp:
                # Some compatible endpoints emit keep-alive chunks with empty choices.
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except AuthenticationError as e:
            raise AIProviderError(f"API key 认证失败：{_msg(e)}") from e
        except PermissionDeniedError as e:
            raise AIProviderError(
                f"模型访问被拒绝（模型：{model}）。请检查 API key 是否开通该模型。原始：{_msg(e)}"
            ) from e
        except APIConnectionError as e:
            raise AIProviderError(f"网络连接失败：{_msg(e)}") from e
        except APIError as e:
            raise AIProviderError(f"API 错误：{_msg(e)}") from e


def _msg(e: APIError) -> str:
    """Extract a short error message from an OpenAI SDK exception."""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        err = body.get("error") or {}
        msg = err.get("message")
        if msg:
            return str(msg)
    return str(e)
