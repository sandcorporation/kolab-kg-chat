"""ContextTrimmer (이슈 02) — 토큰 예산 트리밍 딥모듈.

매 모델 호출 직전 메시지를 토큰 예산 내로 줄인다. 시스템 프롬프트는 항상 유지하고
최근 메시지를 우선 보존한다(멀티턴 누적 + 턴 내 도구출력 누적 둘 다 방어). 토큰 카운터는
주입 가능(운영=모델 토크나이저, 테스트=결정적 카운터).
"""
from __future__ import annotations

from langchain_core.messages import trim_messages


class ContextTrimmer:
    def __init__(self, max_tokens: int, token_counter):
        self._max = max_tokens
        self._counter = token_counter  # callable(list[msg])->int 또는 BaseLanguageModel

    def trim(self, messages: list) -> list:
        try:
            return trim_messages(
                messages,
                max_tokens=self._max,
                token_counter=self._counter,
                strategy="last",          # 최근 메시지 우선 보존
                include_system=True,       # 시스템 프롬프트 항상 유지
                start_on="human",          # 도구 호출/응답 쌍이 끊기지 않게 human 경계에서 시작
                allow_partial=False,
            )
        except Exception:  # noqa: BLE001 — 트리밍 실패는 응답을 막지 않는다(안전망)
            return messages
