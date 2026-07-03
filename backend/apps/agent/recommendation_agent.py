"""RecommendationAgent (이슈 03) — langgraph tool-calling 에이전트.

LLM은 그래프 도구(find_products/find_compatible/get_attributes)로만 근거를 수집하고,
recommend(ids)로 최종 선택을 선언한 뒤 한국어 추천 근거(rationale)를 작성한다.
상품/URL/이미지는 시스템이 결정적으로 부착하므로(ProductEnricher) LLM은 지어내지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from .tools import GraphTools

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
    "5) 상품 URL·이미지는 시스템이 자동으로 붙이므로 링크를 직접 만들지 않는다."
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
        self._agent = create_react_agent(model, self._build_tools(tools), prompt=SYSTEM_PROMPT)

    def _build_tools(self, t: GraphTools) -> list[StructuredTool]:
        async def _search_products(keyword: str, limit: int = 10) -> list[dict]:
            return await t.search_products(keyword, limit=limit)

        async def _find_products(conditions: list[Condition]) -> list[str]:
            return await t.find_products([c.model_dump() for c in conditions])

        async def _find_compatible(product_id: str, depth: int = 3) -> list[dict]:
            return await t.find_compatible(product_id, depth=depth)

        async def _get_attributes(product_id: str) -> list[dict]:
            return await t.get_attributes(product_id)

        async def _recommend(ids: list[str]) -> dict:
            return await t.recommend(ids)

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

        built.append(StructuredTool.from_function(
            coroutine=_recommend, name="recommend",
            description="최종 추천 상품 id를 선언한다.",
            args_schema=RecommendArgs,
        ))
        return built

    @property
    def _config(self) -> dict:
        return {"recursion_limit": self._max * 2 + 1}

    async def run(self, query: str) -> AgentResult:
        self._tools.recommended = []
        state = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=query)]}, config=self._config
        )
        rationale = state["messages"][-1].content
        return AgentResult(rationale=rationale, recommended_ids=list(self._tools.recommended))

    async def astream(self, query: str):
        """추천 근거 토큰을 흘리고, 마지막에 최종 선택 id를 알린다.

        yields: {"type": "token", "content": str} ... {"type": "result", "recommended_ids": [...]}
        도구 호출 라운드의 빈 콘텐츠는 걸러지고 최종 rationale 토큰만 방출된다.
        """
        self._tools.recommended = []
        streamed = False
        final_content = ""
        async for event in self._agent.astream_events(
            {"messages": [HumanMessage(content=query)]}, version="v2", config=self._config
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    streamed = True
                    yield {"type": "token", "content": content}
            elif kind == "on_chat_model_end":
                content = _output_content(event["data"].get("output"))
                if content:
                    final_content = content
        # 토큰 스트리밍을 지원하지 않는 모델은 마지막 rationale을 단어 단위로 폴백 방출한다.
        if not streamed and final_content:
            for word in final_content.split(" "):
                yield {"type": "token", "content": word + " "}
        yield {"type": "result", "recommended_ids": list(self._tools.recommended)}


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
