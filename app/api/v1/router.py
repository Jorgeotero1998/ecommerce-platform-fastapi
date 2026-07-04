from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, health, shop, users

api_router_v1 = APIRouter()

api_router_v1.include_router(health.router, tags=["health"])
api_router_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router_v1.include_router(users.router, prefix="/users", tags=["users"])
api_router_v1.include_router(shop.router, tags=["shop"])
api_router_v1.include_router(ai.router, prefix="/ai", tags=["ai"])

