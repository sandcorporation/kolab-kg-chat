"""OpenAI 호출 동시성 제어 + 백오프 (이슈 24, ADR-0007).

100 동시 챗의 진짜 천장은 OpenAI 레이트 리밋이다. 세마포어로 동시 호출 상한을
두고(초과분은 큐잉), 레이트 오류엔 지수 백오프로 재시도한다. 비전(쓰기)과 챗(읽기)은
각자의 Limiter 인스턴스로 버짓을 분리한다.
"""
from __future__ import annotations

import asyncio


class RateLimitError(Exception):
    """레이트 리밋 신호(제공자 어댑터가 이 예외로 변환)."""


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)

    async def run(self, fn, *args, **kwargs):
        async with self._sem:
            return await fn(*args, **kwargs)


async def with_backoff(
    fn, *args, retries: int = 5, base_delay: float = 0.01, exc=RateLimitError, **kwargs
):
    delay = base_delay
    for attempt in range(retries + 1):
        try:
            return await fn(*args, **kwargs)
        except exc:
            if attempt == retries:
                raise
            if delay:
                await asyncio.sleep(delay)
            delay *= 2


class RateLimitedLLM:
    """LLMClient를 감싸 동시성 상한 + 백오프를 적용한다."""

    def __init__(self, inner, limiter: ConcurrencyLimiter, retries: int = 5, base_delay: float = 0.01):
        self._inner = inner
        self._limiter = limiter
        self._retries = retries
        self._base_delay = base_delay

    async def complete(self, prompt: str) -> str:
        return await self._limiter.run(
            with_backoff,
            self._inner.complete,
            prompt,
            retries=self._retries,
            base_delay=self._base_delay,
        )
