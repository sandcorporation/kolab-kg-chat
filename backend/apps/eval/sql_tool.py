"""SQLTool (이슈 02) — config 1 베이스라인용 읽기전용 text-to-SQL 실행기.

에이전트가 생성한 SELECT를 소스 DB에 안전하게 실행한다. 가드레일: 단일 SELECT만 허용,
쓰기/DDL 거부, LIMIT 강제(max_rows로 캡), 타임아웃. 결과는 dict 행 목록.
"""
from __future__ import annotations

import re

import aiomysql

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|into|call|"
    r"load|handler|lock|rename|set)\b",
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(r"\blimit\s+(\d+)", re.IGNORECASE)


def _sanitize(sql: str, max_rows: int, allowed_table: str | None) -> tuple[str | None, str]:
    """(정제된 SQL, 오류메시지). 안전하지 않으면 (None, 사유)."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        return None, "거부: 한 번에 하나의 문장만 허용됩니다."
    if not re.match(r"(?is)^\s*select\b", s):
        return None, "거부: 읽기전용 SELECT만 허용됩니다."
    if _FORBIDDEN.search(s):
        return None, "거부: 쓰기/DDL 키워드가 포함되어 있습니다."
    if allowed_table is not None:
        # 코퍼스 스코핑: 지정 뷰만 조회하고 기반 테이블 직접 접근을 막는다(공정한 검색 범위).
        if allowed_table.lower() not in s.lower():
            return None, f"거부: {allowed_table} 뷰만 조회할 수 있습니다."
        if re.search(r"\bg5_shop_item(_option|_field_info)?\b", s, re.IGNORECASE):
            return None, f"거부: 기반 테이블 대신 {allowed_table} 뷰를 사용하세요."
    m = _LIMIT_RE.search(s)
    if m:
        if int(m.group(1)) > max_rows:
            s = _LIMIT_RE.sub(f"LIMIT {max_rows}", s, count=1)
    else:
        s = f"{s} LIMIT {max_rows}"
    return s, ""


class SQLTool:
    def __init__(self, connect_factory, max_rows: int = 20, timeout_s: float = 10.0,
                 allowed_table: str | None = None):
        self._connect = connect_factory
        self._max_rows = max_rows
        self._timeout = timeout_s
        self._allowed_table = allowed_table

    async def query(self, sql: str):
        """SELECT를 실행해 행 목록을 반환한다. 안전하지 않으면 거부 문자열."""
        safe, err = _sanitize(sql, self._max_rows, self._allowed_table)
        if safe is None:
            return err
        conn = await self._connect()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SET SESSION MAX_STATEMENT_TIME=%s", (self._timeout,))
                await cur.execute(safe)
                rows = await cur.fetchall()
        except Exception as exc:  # noqa: BLE001 — 잘못된 SQL은 오류 문자열로
            return f"쿼리 오류: {str(exc)[:200]}"
        finally:
            conn.close()
        return [dict(r) for r in rows]
