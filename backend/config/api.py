"""Ninja API root. Routers are attached here."""
from ninja import NinjaAPI

from apps.agent.api import router as agent_router
from apps.core.api import router as core_router

api = NinjaAPI(title="Kolab KG Chat API", version="0.1.0")
api.add_router("", core_router)
api.add_router("", agent_router)
