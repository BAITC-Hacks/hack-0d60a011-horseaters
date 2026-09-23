"""Identity and timestamps for plain Python domain entities."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: UUID = field(default_factory=uuid4)
