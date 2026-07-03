"""SSE 스트리밍 뷰 (ADR-0007/0011). 프론트는 React(nginx가 서빙)."""
import json

from django.http import StreamingHttpResponse

from apps.agent.runtime import build_default_context, get_agent_context, set_agent_context
from apps.agent.streaming import agent_event_stream


def _context():
    """설정된 에이전트 컨텍스트가 없으면 운영 그래프 기반 컨텍스트를 조립한다."""
    try:
        return get_agent_context()
    except RuntimeError:
        context = build_default_context()
        set_agent_context(context)
        return context


async def chat_stream(request):
    try:
        body = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}
    query = body.get("query", "")

    context = _context()
    response = StreamingHttpResponse(
        agent_event_stream(context.agent, context.enricher, query),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Nginx 버퍼링 방지(ADR-0007)
    return response
