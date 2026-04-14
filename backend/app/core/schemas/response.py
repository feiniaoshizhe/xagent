"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:49
Description:
FilePath: response
"""
from datetime import datetime
from typing import Any, Annotated

from pydantic import BaseModel, WrapValidator, ConfigDict
from pydantic_core.core_schema import ValidatorFunctionWrapHandler, ValidationInfo


def maybe_strip_whitespace(
        v: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
) -> int:
    return v


def datetime_to_gmt_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


model_config = ConfigDict(
    json_encoders={datetime: datetime_to_gmt_str},
    populate_by_name=True,
)


class CustomModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: datetime_to_gmt_str},
        populate_by_name=True,
    )


def result_response(data_model=None, validate: bool = True):
    data_model = data_model if data_model is not None else dict
    class ResponseModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: data_model = {}
        message: str = "Success"
        trace_id: str = ""

    class ResponseSoftModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: Annotated[data_model, WrapValidator(maybe_strip_whitespace)] = {}
        message: str = "Success"
        trace_id: str = ""

    if validate:
        return ResponseModel
    else:
        return ResponseSoftModel


def list_response(data_model, validate: bool = True):
    class ListResponseModel(CustomModel):
        model_config = model_config
        items: list[data_model]

    class ResponseModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: ListResponseModel
        message: str = "Success"
        trace_id: str = ""

    class ResponseSoftModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: Annotated[ListResponseModel, WrapValidator(maybe_strip_whitespace)] = None
        message: str = "Success"
        trace_id: str = ""

    if validate:
        return ResponseModel
    else:
        return ResponseSoftModel


def pager_response(data_model, validate: bool = True):
    class ListResponseModel(CustomModel):
        model_config = model_config
        per_page: int
        page: int
        pages: int
        total: int
        items: list[data_model]

    class ResponseModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: ListResponseModel
        message: str = "Success"
        trace_id: str = ""

    class ResponseSoftModel(CustomModel):
        model_config = model_config
        code: int = 0
        data: Annotated[ListResponseModel, WrapValidator(maybe_strip_whitespace)] = None
        message: str = "Success"
        trace_id: str = ""

    if validate:
        return ResponseModel
    else:
        return ResponseSoftModel
