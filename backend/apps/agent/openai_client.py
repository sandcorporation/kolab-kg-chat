"""OpenAI 어댑터 (이슈 26 B).

LLMClient/VisionClient Protocol을 OpenAI로 구현하고, 토큰 사용량을 누적해
비용 산출에 쓴다. 키는 env `OPEN_AI_KEY`에서 읽는다. (임베딩은 제거됨, ADR-0010)
"""
from __future__ import annotations

import os
from functools import lru_cache

from openai import AsyncOpenAI

_usage = {"chat_in": 0, "chat_out": 0}


def get_usage() -> dict:
    return dict(_usage)


def reset_usage() -> None:
    for k in _usage:
        _usage[k] = 0


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])


class OpenAILLM:
    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def complete(self, prompt: str) -> str:
        resp = await _client().chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        if resp.usage:
            _usage["chat_in"] += resp.usage.prompt_tokens
            _usage["chat_out"] += resp.usage.completion_tokens
        return resp.choices[0].message.content or "{}"


class OpenAIVisionClient:
    """VisionClient Protocol(이슈 10)을 OpenAI 비전(gpt-4o)으로 구현 (이슈 02, ADR-0005)."""

    def __init__(self, model: str | None = None):
        self.model_version = model or os.environ.get("OPENAI_VISION_MODEL", "gpt-4o")

    async def extract(self, image_urls: list[str], prompt: str) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        content += [{"type": "image_url", "image_url": {"url": u}} for u in image_urls]
        resp = await _client().chat.completions.create(
            model=self.model_version,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        if resp.usage:
            _usage["chat_in"] += resp.usage.prompt_tokens
            _usage["chat_out"] += resp.usage.completion_tokens
        return resp.choices[0].message.content or "{}"
