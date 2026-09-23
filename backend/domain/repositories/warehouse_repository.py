from typing import Protocol
from uuid import UUID


class WarehouseRepository(Protocol):
    def list_active_ids(self) -> list[UUID]: ...
