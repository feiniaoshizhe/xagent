from fastapi.routing import APIRouter
from app.web.api.v1 import users
from app.web.api.v1 import dummy
from app.web.api.v1 import redis
from app.web.api.v1 import rabbit
from app.web.api import docs
from app.web.api.v1 import monitoring
from app.web.api.v1 import sources
from app.web.api.v1 import agent_config

api_router = APIRouter()
api_router.include_router(docs.router)
api_router.include_router(monitoring.router)
api_router.include_router(users.router)

api_router.include_router(dummy.router, prefix="/dummy", tags=["dummy"])
api_router.include_router(redis.router, prefix="/redis", tags=["redis"])
api_router.include_router(rabbit.router, prefix="/rabbit", tags=["rabbit"])


api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(agent_config.router,prefix="/agent",tags=["agent-config"])
