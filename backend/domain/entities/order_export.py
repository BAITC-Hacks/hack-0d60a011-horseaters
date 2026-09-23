from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .enums import ExportFormat


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderExport:
    purchase_order_id: UUID
    format: ExportFormat
    file_name: str
    file_checksum: str
    created_by: UUID
    created_at: datetime = field(default_factory=utc_now)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.file_name.strip():
            raise ValueError("file_name must not be empty")
        if len(self.file_checksum) != 64:
            raise ValueError("file_checksum must be a SHA-256 hexadecimal digest")
        try:
            int(self.file_checksum, 16)
        except ValueError as error:
            raise ValueError("file_checksum must be a SHA-256 hexadecimal digest") from error
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must contain timezone information")
