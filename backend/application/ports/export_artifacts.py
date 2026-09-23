from typing import Protocol
from uuid import UUID


class ExportArtifactUnavailableError(RuntimeError):
    pass


class ExportArtifactStore(Protocol):
    def put(self, export_id: UUID, content: bytes) -> None:
        """Write a complete immutable artifact or raise; never overwrite an existing artifact."""
        ...

    def read(self, export_id: UUID) -> bytes: ...
