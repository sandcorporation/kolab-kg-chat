"""RecommendationAgent (이슈 03) — langgraph tool-calling 에이전트.

LLM은 그래프 도구(find_products/find_compatible/get_attributes)로만 근거를 수집하고,
recommend(ids)로 최종 선택을 선언한 뒤 한국어 추천 근거(rationale)를 작성한다.
상품/URL/이미지는 시스템이 결정적으로 부착하므로(ProductEnricher) LLM은 지어내지 않는다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import BaseModel, Field

from .context_trim import ContextTrimmer
from .history import history_to_messages
from .tools import GraphTools


class AgentState(TypedDict):
    """그래프 state — 대화 메시지 + 추천 포착(사이드채널 대신 state)."""
    messages: Annotated[list, add_messages]
    recommended_ids: list[str]

# 도구 호출 진행 상태 라벨(백엔드 매핑) — 첫 토큰 전 전환형 상태줄에 표시된다.
TOOL_STATUS_LABELS = {
    "search_products": "상품 검색 중…",
    "find_products": "상품 검색 중…",
    "semantic_search": "의미 유사 상품 검색 중…",
    "find_compatible": "호환 상품 확인 중…",
    "get_attributes": "상품 속성 조회 중…",
    "recommend": "추천 정리 중…",
}

SYSTEM_PROMPT = (
    "당신은 실험·연구 장비 쇼핑몰(kolabshop)의 상품 추천 도우미입니다.\n"
    "작업 순서:\n"
    "1) 먼저 search_products(keyword)로 후보를 찾는다. 사용자의 자연어에서 핵심 명사를 뽑아 "
    "한국어와 영어 키워드를 각각 시도한다(예: '유리 플라스크' → '플라스크', 'flask'). "
    "카탈로그 상품명은 한/영이 섞여 있으니 결과가 없으면 다른 키워드로 1~2회 더 시도한다.\n"
    "2) 필요하면 get_attributes(id)로 후보의 속성을 확인해 요구조건 부합 여부를 판단한다. "
    "속성 정밀 필터가 필요하면 find_products(conditions)를, 호환 부속품이 필요하면 find_compatible을 쓴다.\n"
    "3) 사용자의 요청과 실제로 관련된 상품만 recommend(ids)로 선언한다(보통 1~5개). "
    "적합한 후보가 없으면 recommend를 호출하지 말고, 더 구체적으로 되물어라.\n"
    "4) 마지막 메시지에 한국어로 간결한 추천 근거를 쓴다. 근거는 도구로 확인한 상품명·속성에 기반해야 하며, "
    "카탈로그에 없는 상품이나 속성을 지어내지 말라.\n"
    "5) 상품 URL·이미지는 시스템이 자동으로 붙이므로 링크를 직접 만들지 않는다.\n"
    "6) 후속 질문이 이전에 추천된 특정 상품을 가리키면('그 첫 번째 상품', '두 번째 거' 등), "
    "대화 맥락에서 그 상품을 특정해 상품명과 맥락 정보로 자신 있게 답한다.\n"
    "7) 그러나 사용자가 카탈로그 전반을 묻거나('어떤 상품 있어?', '뭐 있어?', '무슨 상품들이야?') "
    "직전 되묻기에 답하지 않고 화제를 바꾸면, 이 질문은 특정 상품 검색이 아니다. 이때는 도구를 "
    "호출하지 말고, 직전 주제(예: 핀셋)를 답변에 언급조차 하지 말고, 곧바로 대표 카테고리"
    "(유리기구·피펫·시약·교반기·클램프·용기·측정기 등)를 안내하며 어떤 용도를 찾는지 되묻는다."
)


class Condition(BaseModel):
    name: str = Field(description="속성 이름 (예: material, capacity_ml)")
    op: str = Field(description="비교 연산자: ==, <=, >=, <, >")
    value: str | float = Field(description="비교 값")


class SearchArgs(BaseModel):
    keyword: str = Field(description="상품명 검색어(한/영). 예: 플라스크, flask")
    limit: int = 10


class FindProductsArgs(BaseModel):
    conditions: list[Condition] = Field(description="AND로 결합되는 속성 조건 목록")


class FindCompatibleArgs(BaseModel):
    product_id: str
    depth: int = 3


class ProductIdArg(BaseModel):
    product_id: str


class RecommendArgs(BaseModel):
    ids: list[str] = Field(description="최종 추천 상품 source_id 목록")


class SemanticArgs(BaseModel):
    keyword: str = Field(description="의미 유사도 검색어(자연어). 상품명 키워드로 못 잡는 서술형 질의에.")
    k: int = 10


def _output_content(output) -> str:
    """on_chat_model_end 출력에서 텍스트 콘텐츠를 견고하게 추출한다."""
    if output is None:
        return ""
    content = getattr(output, "content", None)
    if content is None and isinstance(output, dict):
        content = output.get("content")
    if isinstance(content, list):  # 멀티모달 파트 → 텍스트만 이어붙임
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


@dataclass
class AgentResult:
    rationale: str
    recommended_ids: list[str] = field(default_factory=list)


class RecommendationAgent:
    def __init__(self, model, tools: GraphTools, max_iterations: int = 8, semantic_tool=None):
        self._tools = tools
        self._semantic_tool = semantic_tool  # ADR-0012: 의미 유사도 검색 도구(선택)
        self._max = max_iterations
        built = self._build_tools(tools)
        self._llm = model.bind_tools(built)  # 도구 바인딩 모델(scripted는 무시)
        # 컨텍스트 방어: 매 모델 호출 직전 토큰 예산 트림(카운터=원본 모델 토크나이저).
        budget = int(os.environ.get("AGENT_TOKEN_BUDGET", "6000"))
        self._trimmer = ContextTrimmer(budget, token_counter=model)
        self._history_turns = int(os.environ.get("AGENT_HISTORY_TURNS", "5"))
        self._graph = self._build_graph(built)

    def _build_graph(self, built: list[StructuredTool]):
        """직접 짠 StateGraph: START → prepare → agent ⇄ tools → END (ADR: 노드+엣지)."""
        async def prepare(state: AgentState) -> dict:
            # 이슈 04에서 클라이언트 히스토리 병합. 트레이서 단계는 통과.
            return {}

        async def agent(state: AgentState) -> dict:
            # 매 호출 직전 토큰 예산 트림(시스템 유지 + 최근 우선).
            msgs = self._trimmer.trim([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
            response = await self._llm.ainvoke(msgs)
            return {"messages": [response]}

        def route(state: AgentState):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        g = StateGraph(AgentState)
        g.add_node("prepare", prepare)
        g.add_node("agent", agent)
        g.add_node("tools", ToolNode(built))
        g.add_edge(START, "prepare")
        g.add_edge("prepare", "agent")
        g.add_conditional_edges("agent", route, {"tools": "tools", END: END})
        g.add_edge("tools", "agent")
        return g.compile()

    def _build_tools(self, t: GraphTools) -> list[StructuredTool]:
        async def _search_products(keyword: str, limit: int = 10) -> list[dict]:
            return await t.search_products(keyword, limit=limit)

        async def _find_products(conditions: list[Condition]) -> list[str]:
            return await t.find_products([c.model_dump() for c in conditions])

        async def _find_compatible(product_id: str, depth: int = 3) -> list[dict]:
            return await t.find_compatible(product_id, depth=depth)

        async def _get_attributes(product_id: str) -> list[dict]:
            return await t.get_attributes(product_id)

        async def _recommend(ids: list[str], tool_call_id: Annotated[str, InjectedToolCallId]):
            # 사이드채널 대신 그래프 state 갱신(요청별 격리 = 동시요청 레이스 제거).
            return Command(update={
                "recommended_ids": list(ids),
                "messages": [ToolMessage(
                    f"{len(ids)}개 상품을 추천으로 선언했습니다.", tool_call_id=tool_call_id)],
            })

        built = [
            StructuredTool.from_function(
                coroutine=_search_products, name="search_products",
                description="상품명 키워드로 후보 상품(id·이름)을 찾는다. 자연어 질의의 진입 도구.",
                args_schema=SearchArgs,
            ),
            StructuredTool.from_function(
                coroutine=_find_products, name="find_products",
                description="속성 조건(AND)을 충족하는 상품 id 목록을 반환한다.",
                args_schema=FindProductsArgs,
            ),
            StructuredTool.from_function(
                coroutine=_find_compatible, name="find_compatible",
                description="주어진 상품과 호환되는(연결된) 상품을 탐색한다.",
                args_schema=FindCompatibleArgs,
            ),
            StructuredTool.from_function(
                coroutine=_get_attributes, name="get_attributes",
                description="특정 상품의 상세 속성(추천 근거)을 반환한다.",
                args_schema=ProductIdArg,
            ),
        ]

        # ADR-0012: 의미 유사도 검색(키워드·속성으로 못 잡는 서술형 질의 보강)
        if self._semantic_tool is not None:
            async def _semantic_search(keyword: str, k: int = 10) -> list[dict]:
                return await self._semantic_tool.search(keyword, k=k)

            built.append(StructuredTool.from_function(
                coroutine=_semantic_search, name="semantic_search",
                description="의미 유사도로 top-k 상품(id·이름)을 찾는다. 상품명 키워드로 못 잡는 서술형 질의에.",
                args_schema=SemanticArgs,
            ))

        # args_schema 미지정 → InjectedToolCallId가 모델 노출 스키마에서 자동 제외된다.
        built.append(StructuredTool.from_function(
            coroutine=_recommend, name="recommend",
            description="최종 추천 상품 source_id 목록을 선언한다.",
        ))
        return built

    @property
    def _config(self) -> dict:
        return {"recursion_limit": self._max * 2 + 1}

    def _initial_state(self, query: str, history=None) -> dict:
        # 무상태 멀티턴: 클라이언트 히스토리(최근 N턴)를 현재 질의 앞에 놓는다.
        msgs = history_to_messages(history, max_turns=self._history_turns)
        msgs.append(HumanMessage(content=query))
        return {"messages": msgs, "recommended_ids": []}

    async def run(self, query: str, history=None) -> AgentResult:
        state = await self._graph.ainvoke(self._initial_state(query, history), config=self._config)
        rationale = _output_content(state["messages"][-1])
        return AgentResult(
            rationale=rationale, recommended_ids=list(state.get("recommended_ids") or [])
        )

    async def astream(self, query: str, history=None):
        """추천 근거 토큰을 흘리고, 마지막에 최종 선택 id를 알린다.

        yields: {"type": "status", "label": str} ... {"type": "token", "content": str}
                ... {"type": "result", "recommended_ids": [...]}
        도구 호출 라운드의 빈 콘텐츠는 걸러지고 최종 rationale 토큰만 방출된다.
        토큰 전 도구 호출은 status로 진행 상황을 알린다(전환형 상태줄).
        추천 id는 그래프 최종 state(루트 실행의 on_chain_end)에서 읽는다.
        """
        streamed = False
        final_content = ""
        recommended: list[str] = []
        root_run_id = None
        async for event in self._graph.astream_events(
            self._initial_state(query, history), version="v2", config=self._config
        ):
            if root_run_id is None and event["event"] == "on_chain_start":
                root_run_id = event["run_id"]  # 최상위 그래프 실행 id
            kind = event["event"]
            if kind == "on_tool_start":
                label = TOOL_STATUS_LABELS.get(event.get("name", ""))
                if label:
                    yield {"type": "status", "label": label}
            elif kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    streamed = True
                    yield {"type": "token", "content": content}
            elif kind == "on_chat_model_end":
                content = _output_content(event["data"].get("output"))
                if content:
                    final_content = content
            elif kind == "on_chain_end" and event["run_id"] == root_run_id:
                out = event["data"].get("output")
                if isinstance(out, dict) and "recommended_ids" in out:
                    recommended = list(out.get("recommended_ids") or [])
        # 토큰 스트리밍을 지원하지 않는 모델은 마지막 rationale을 단어 단위로 폴백 방출한다.
        if not streamed and final_content:
            for word in final_content.split(" "):
                yield {"type": "token", "content": word + " "}
        yield {"type": "result", "recommended_ids": recommended}


def build_openai_agent(tools: GraphTools, model_name: str | None = None, **kwargs) -> RecommendationAgent:
    """실제 경로: ChatOpenAI 기반 에이전트."""
    import os

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ["OPEN_AI_KEY"],
        temperature=0,
    )
    return RecommendationAgent(model, tools, **kwargs)
