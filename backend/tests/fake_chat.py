"""툴콜을 스크립트하는 fake ChatModel — RecommendationAgent 테스트용."""
from __future__ import annotations

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedChatModel(BaseChatModel):
    """호출 순서대로 미리 정한 AIMessage를 반환한다(툴콜 포함)."""

    responses: list[AIMessage]
    idx: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001 - 스크립트라 바인딩 무시
        return self

    def _next(self) -> AIMessage:
        msg = self.responses[self.idx]
        self.idx += 1
        return msg

    def _generate(
        self,
        messages: list[BaseMessage],
        stop=None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next())])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop=None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next())])
