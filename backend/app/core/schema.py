"""Shared Pydantic schema helpers."""

from pydantic import BaseModel, ConfigDict


class CustomModel(BaseModel):
    """
    Base schema using
    """

    model_config = ConfigDict(

        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )
