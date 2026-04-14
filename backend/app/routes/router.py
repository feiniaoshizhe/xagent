from fastapi.routing import APIRouter

from app.routes.v1 import monitoring, redis, rabbit, users, docs, agent_flow

api_router = APIRouter()
api_router.include_router(docs.router)
api_router.include_router(monitoring.router)
api_router.include_router(users.router)


api_router.include_router(redis.router, prefix="/redis", tags=["redis"])
api_router.include_router(rabbit.router, prefix="/rabbit", tags=["rabbit"])
api_router.include_router(agent_flow.router, prefix="/agent_flow", tags=["agent_flows"])
