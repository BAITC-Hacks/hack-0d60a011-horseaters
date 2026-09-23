from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from backend.application.dto.imports import ImportFileCommand, ParsedImport
from backend.domain.entities.imports import ImportBatch


class ImportFileReader(Protocol):
    def read(self, command: ImportFileCommand) -> ParsedImport: ...


class ImportGateway(Protocol):
    def start(self, command: ImportFileCommand, *, checksum: str) -> ImportBatch: ...

    def complete(self, batch: ImportBatch, parsed: ParsedImport) -> ImportBatch: ...

    def fail(
        self,
        batch: ImportBatch,
        *,
        error_details: Mapping[str, Any],
    ) -> ImportBatch: ...
