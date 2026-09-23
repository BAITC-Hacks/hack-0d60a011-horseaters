from typing import Any
from uuid import UUID

from pydantic import BaseModel

from backend.domain.enums import ImportSourceType, ImportStatus


class ImportResponse(BaseModel):
    batch_id: UUID
    source_type: ImportSourceType
    status: ImportStatus
    row_count: int
    file_checksum: str


class ImportStatusResponse(ImportResponse):
    file_name: str
    error_details: dict[str, Any] | None = None
