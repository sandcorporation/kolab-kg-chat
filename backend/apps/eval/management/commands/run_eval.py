"""리트리벌 ablation 전체 실행 (이슈 06) — configs×queries 실행→쌍별 순서스왑 심사→리포트.

모든 LLM 산출(에이전트 답변·심사)은 캐시되어 재실행은 새 것만 비용. 429는 백오프 재시도.

    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root \
      -e SOURCE_DB_PASSWORD=root -e SOURCE_DB_NAME=kolabshop \
      api python manage.py run_eval
"""
import asyncio
import json
import os
from itertools import combinations
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.eval.config import build_eval_context
from apps.eval.judge import Judge, aggregate, combine
from apps.eval.queries import EvalQueries
from apps.eval.runner import EvalRunner
from apps.eval.scorer import Scorer, aggregate_scores, make_openai_score_fn

CONFIG_IDS = ["config1", "config2", "config3", "config4", "config5"]
CONFIG_LABEL = {
    "config1": "SQL", "config2": "graph(structured)",
    "config3": "+vision", "config4": "+embeddings", "config5": "hybrid+rerank",
    "rag": "RAG(질의이해→검색→읽기)",
}


async def _retry(fn, *, tries=5):
    for attempt in range(tries):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if ("429" in msg or "rate limit" in msg) and attempt < tries - 1:
                await asyncio.sleep(5 * (attempt + 1))
                continue
            raise


def _fmt_answer(ans: dict) -> str:
    lines = [f"근거: {ans.get('rationale', '')[:400]}", "추천 상품:"]
    for p in ans.get("products", [])[:6]:
        tags = ", ".join(f"{g['name']}={g['value']}" for g in (p.get("grounding") or [])[:4])
        lines.append(f"- {p.get('name', '')}" + (f" [{tags}]" if tags else ""))
    return "\n".join(lines)


def _make_judge_fn(model: str):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])

    async def judge_fn(query_text, first, second):
        prompt = (
            f'사용자 질의: "{query_text}"\n\n'
            "아래 두 추천 결과 중 질의에 더 적합한 쪽을 고르라. 상품의 관련성과 근거의 타당성을 본다.\n\n"
            f"[결과 1]\n{_fmt_answer(first)}\n\n[결과 2]\n{_fmt_answer(second)}\n\n"
            '더 나은 쪽이 1이면 "1", 2이면 "2", 우열을 가리기 어려우면 "tie". '
            'JSON {"winner":"1|2|tie"}만 출력.'
        )
        resp = await client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0,
        )
        return json.loads(resp.choices[0].message.content).get("winner", "tie")

    return judge_fn


def _fmt_products(ans: dict, n: int = 4) -> str:
    names = [p.get("name", "")[:42] for p in (ans or {}).get("products", [])[:n]]
    return " · ".join(names) if names else "(추천 없음)"


def _render(agg: dict, score_agg: dict, queries: list, answers: dict, judge_model: str) -> str:
    out = ["# 리트리벌 스택 검색 품질 ablation — 결과\n",
           f"코퍼스 250 · 쿼리 {len(queries)} · 심사/채점 {judge_model} · 에이전트 temp=0\n",
           "config: " + " · ".join(f"{c}={CONFIG_LABEL[c]}" for c in CONFIG_IDS) + "\n"]

    # 절대 적합도 점수(헤드라인) — "다 낮은가?"를 절대 척도로 본다
    out.append("## 절대 적합도 점수 (0~3, 높을수록 좋음)\n")
    out.append("| config | 전체 평균 | " + " | ".join(score_agg["by_stratum"].keys()) + " |")
    out.append("|---|---|" + "---|" * len(score_agg["by_stratum"]))
    for c in sorted(score_agg["overall"], key=lambda x: -score_agg["overall"][x]):
        row = [f"{c} ({CONFIG_LABEL[c]})", str(score_agg["overall"][c])]
        row += [str(score_agg["by_stratum"][st].get(c, "-")) for st in score_agg["by_stratum"]]
        out.append("| " + " | ".join(row) + " |")

    out.append("\n> 승률 = 쌍별 비교(무승부 많아 합<1). 절대 점수와 함께 본다.\n")
    out.append("## 전체 승률\n")
    out.append("| config | 승 | 비교 | 승률 |")
    out.append("|---|---|---|---|")
    for c in sorted(agg["overall"], key=lambda x: -agg["overall"][x]["win_rate"]):
        e = agg["overall"][c]
        out.append(f"| {c} ({CONFIG_LABEL[c]}) | {e['wins']} | {e['comparisons']} | {e['win_rate']} |")

    out.append("\n## 계층별 승률\n")
    for st, table in agg["by_stratum"].items():
        out.append(f"### {st}")
        out.append("| config | 승 | 비교 | 승률 |")
        out.append("|---|---|---|---|")
        for c in sorted(table, key=lambda x: -table[x]["win_rate"]):
            e = table[c]
            out.append(f"| {c} | {e['wins']} | {e['comparisons']} | {e['win_rate']} |")
        out.append("")

    # 쿼리셋
    out.append("## 쿼리셋\n")
    out.append("| id | 계층 | 질의 |")
    out.append("|---|---|---|")
    for q in queries:
        out.append(f"| {q['query_id']} | {q['stratum']} | {q['text']} |")

    # 쿼리별 config 추천(정성) — config가 실제로 무엇을 추천했는지
    out.append("\n## 쿼리별 config 추천 (상위 상품)\n")
    for q in queries:
        out.append(f"### `{q['query_id']}` [{q['stratum']}] {q['text']}")
        for c in CONFIG_IDS:
            out.append(f"- **{c}** ({CONFIG_LABEL[c]}): {_fmt_products(answers.get((c, q['query_id'])))}")
        out.append("")
    return "\n".join(out)


class Command(BaseCommand):
    help = "리트리벌 ablation 전체 실행 + 리포트."

    def add_arguments(self, parser):
        parser.add_argument("--judge-model", default="gpt-4o")
        parser.add_argument("--agent-version", default="v1")
        parser.add_argument("--configs", default="", help="쉼표구분 config 목록(기본 전체)")
        parser.add_argument("--out", default="/app/eval_report.md")

    def handle(self, *args, **options):
        asyncio.run(self._run(options))

    async def _run(self, o):
        if o.get("configs"):  # A/B용: 지정 config만(예: config4,rag)
            CONFIG_IDS[:] = [c.strip() for c in o["configs"].split(",")]
        queries = await EvalQueries().list()
        runner = EvalRunner(agent_version=o["agent_version"])
        contexts = {c: build_eval_context(c) for c in CONFIG_IDS}

        # 1) configs × queries (캐시)
        answers = {}
        for c in CONFIG_IDS:
            ctx = contexts[c]
            fails = 0
            for q in queries:
                try:
                    ans = await _retry(lambda: runner.run(c, q["query_id"], q["text"], ctx.agent, ctx.enricher))
                except Exception as exc:  # noqa: BLE001 — 재귀한도/오류 → 빈 답(그 쿼리에서 패)
                    ans = {"rationale": f"(agent failed: {str(exc)[:60]})", "products": []}
                    await runner.store_answer(c, q["query_id"], ans)
                    fails += 1
                answers[(c, q["query_id"])] = ans
            self.stdout.write(f"  ran {c} on {len(queries)} queries ({fails} failed)")

        # 1.5) 절대 루브릭 점수 (0~3, 캐시)
        scorer = Scorer(make_openai_score_fn(o["judge_model"]), model=o["judge_model"],
                        agent_version=o["agent_version"])
        score_records = []
        for c in CONFIG_IDS:
            for q in queries:
                s = await _retry(lambda: scorer.score(c, q["query_id"], q["text"], answers[(c, q["query_id"])]))
                score_records.append({"config_id": c, "stratum": q["stratum"], "score": s})
        score_agg = aggregate_scores(score_records)

        # 2) 쌍별 순서스왑 심사 (캐시)
        judge = Judge(_make_judge_fn(o["judge_model"]), model=o["judge_model"])
        records = []
        for q in queries:
            for ca, cb in combinations(CONFIG_IDS, 2):
                aa, ab = answers[(ca, q["query_id"])], answers[(cb, q["query_id"])]
                w1 = await _retry(lambda: judge.verdict(q["query_id"], q["text"], ca, aa, cb, ab, "ab"))
                w2 = await _retry(lambda: judge.verdict(q["query_id"], q["text"], ca, aa, cb, ab, "ba"))
                records.append({"stratum": q["stratum"], "config_a": ca, "config_b": cb,
                                "winner": combine(w1, w2)})
            self.stdout.write(f"  judged {q['query_id']}")

        # 3) 집계 + 리포트
        agg = aggregate(records)
        report = _render(agg, score_agg, queries, answers, o["judge_model"])
        Path(o["out"]).write_text(report, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\n{report}\n\nreport written to {o['out']}"))
