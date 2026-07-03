"""이슈 24 — 동시성 리미터 + 백오프 (DB 불필요)."""
import asyncio

from apps.agent.rate_limit import (
    ConcurrencyLimiter,
    RateLimitedLLM,
    RateLimitError,
)


class TrackingLLM:
    def __init__(self):
        self.current = 0
        self.peak = 0

    async def complete(self, prompt: str) -> str:
        self.current += 1
        self.peak = max(self.peak, self.current)
        await asyncio.sleep(0.02)
        self.current -= 1
        return "ok"


class FlakyLLM:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RateLimitError()
        return "ok"


async def test_concurrency_capped_at_limit():
    tracking = TrackingLLM()
    llm = RateLimitedLLM(tracking, ConcurrencyLimiter(2))
    await asyncio.gather(*[llm.complete("p") for _ in range(10)])
    assert tracking.peak <= 2


async def test_excess_calls_are_queued_and_complete():
    tracking = TrackingLLM()
    llm = RateLimitedLLM(tracking, ConcurrencyLimiter(1))
    results = await asyncio.gather(*[llm.complete("p") for _ in range(5)])
    assert results == ["ok"] * 5
    assert tracking.peak == 1


async def test_backoff_retries_on_rate_error():
    flaky = FlakyLLM(fail_times=2)
    llm = RateLimitedLLM(flaky, ConcurrencyLimiter(5), retries=5, base_delay=0)
    assert await llm.complete("p") == "ok"
    assert flaky.calls == 3  # 2회 실패 후 성공


async def test_backoff_gives_up_after_retries():
    flaky = FlakyLLM(fail_times=99)
    llm = RateLimitedLLM(flaky, ConcurrencyLimiter(5), retries=2, base_delay=0)
    try:
        await llm.complete("p")
        assert False, "should have raised"
    except RateLimitError:
        pass
    assert flaky.calls == 3  # 최초 1 + 재시도 2
