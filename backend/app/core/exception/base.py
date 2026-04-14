"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:20
Description:
FilePath: base
"""
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class ApiError(Exception):
    """Raised when an API endpoint needs a structured error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        error: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.status_code = status_code
        self.message = message
        self.error = error or HTTPStatus(status_code).phrase
        self.data = data

    def __str__(self):
        return f"""{self.__class__.__name__}({self.status_code=}, {self.message=}, {self.error=})"""



async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    """Render structured API error responses."""

    payload: dict[str, Any] = {
        "statusCode": exc.status_code,
        "message": exc.message,
        "error": exc.error,
    }
    if exc.data is not None:
        payload["data"] = exc.data
    return JSONResponse(status_code=exc.status_code, content=payload)


def register_error_handlers(app: FastAPI) -> None:
    """Register application exception handlers."""

    app.add_exception_handler(ApiError, api_error_handler)
