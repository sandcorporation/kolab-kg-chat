"""Core router — health and other infrastructure endpoints."""
from ninja import Router

from apps.core.db import check_db_health

router = Router()


@router.get("/health")
async def health(request):
    """리브니스 + DB(age·vector 확장) 가용성 체크 (이슈 02)."""
    db = await check_db_health()
    ok = db["connected"] and all(db["extensions"].values())
    return {"status": "ok" if ok else "degraded", "db": db}
