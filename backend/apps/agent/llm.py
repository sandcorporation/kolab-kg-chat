"""LLM 클라이언트 인터페이스 (읽기 경로 에이전트용).

운영은 OpenAI를 같은 Protocol로 끼우고, 테스트는 결정적 FakeLLM을 쓴다.
"""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    async def complete(self, prompt: str) -> str:
        ...


class FakeLLM:
    """프롬프트와 무관하게 미리 정한 응답을 돌려주는 테스트용 LLM."""

    def __init__(self, response: str):
        self._response = response
        self.last_prompt: str | None = None

    async def complete(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response
