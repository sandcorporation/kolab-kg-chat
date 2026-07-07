"""슬라이스 01 (ADR-0019) — Reranker 딥모듈: 후보별 0~3 채점 → 임계·top_k 컷."""
from langchain_core.messages import AIMessage

from apps.agent.rerank import LLMReranker
from tests.fake_chat import ScriptedChatModel


def _cand(sid, name="n", desc=""):
    return {"source_id": sid, "name": name, "description": desc}


async def test_rerank_sorts_by_score_and_cuts():
    # 모델이 후보별 0~3 점수를 반환 → 임계(2)↑만, 점수 내림차순, top_k(2) 컷.
    model = ScriptedChatModel(responses=[AIMessage(content="1: 1\n2: 3\n3: 2")])
    reranker = LLMReranker(model, top_k=2, min_score=2)
    cands = [_cand("a"), _cand("b"), _cand("c")]  # 3 > top_k 2 → 리랭크 engage
    out = await reranker.rerank("질의", cands)
    assert [c["source_id"] for c in out] == ["b", "c"]  # b=3, c=2 (a=1 컷)


async def test_rerank_skips_llm_when_within_cap():
    # 후보 수 ≤ top_k → 자를 게 없어 모델 호출 없이 원본 그대로(콜 생략).
    model = ScriptedChatModel(responses=[])  # 호출되면 IndexError
    reranker = LLMReranker(model, top_k=5, min_score=2)
    cands = [_cand("a"), _cand("b"), _cand("c")]  # 3 ≤ 5 → 스킵
    out = await reranker.rerank("질의", cands)
    assert [c["source_id"] for c in out] == ["a", "b", "c"]


async def test_rerank_returns_empty_when_all_below_threshold():
    # 전부 임계 미만 → [] (상위서 재시도 트리거).
    model = ScriptedChatModel(responses=[AIMessage(content="1: 0\n2: 1\n3: 1")])
    reranker = LLMReranker(model, top_k=2, min_score=2)
    out = await reranker.rerank("질의", [_cand("a"), _cand("b"), _cand("c")])
    assert out == []


async def test_rerank_treats_unscored_candidate_as_zero():
    # 모델이 일부만 채점(형식 이탈) → 누락 후보는 0점 취급되어 제외.
    model = ScriptedChatModel(responses=[AIMessage(content="2: 3")])  # a·c 누락
    reranker = LLMReranker(model, top_k=2, min_score=2)
    out = await reranker.rerank("질의", [_cand("a"), _cand("b"), _cand("c")])
    assert [c["source_id"] for c in out] == ["b"]
