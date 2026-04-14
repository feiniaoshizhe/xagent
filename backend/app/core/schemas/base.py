"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:49
Description:
FilePath: base
"""

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
