import os
from pathlib import Path
from uuid import UUID

from backend.application.ports.export_artifacts import ExportArtifactUnavailableError


class FileExportArtifactStore:
    def __init__(self, directory: Path) -> None:
        self._directory = Path(directory)

    def _path(self, export_id: UUID) -> Path:
        if not isinstance(export_id, UUID):
            raise TypeError("Export key must be a UUID")
        return self._directory / f"{export_id}.xlsx"

    def put(self, export_id: UUID, content: bytes) -> None:
        path = self._path(export_id)
        created = False
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                created = True
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            if created:
                path.unlink(missing_ok=True)
            raise ExportArtifactUnavailableError("Cannot store export") from None

    def read(self, export_id: UUID) -> bytes:
        try:
            return self._path(export_id).read_bytes()
        except OSError:
            raise ExportArtifactUnavailableError("Export file unavailable") from None
