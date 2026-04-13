from sqlalchemy.orm import DeclarativeBase
from xagent.db.meta import meta


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta

