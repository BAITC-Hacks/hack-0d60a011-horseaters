from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Stable code/message plus optional endpoint-specific diagnostic fields."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail
    request_id: str = Field(description="Correlation ID also returned in X-Request-ID")


def error_response(
    *, code: str, message: str, request_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = ErrorDetail(code=code, message=message, **(context or {}))
    return ErrorResponse(detail=detail, request_id=request_id).model_dump(exclude_none=True)
