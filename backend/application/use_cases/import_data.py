from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.application.dto.imports import ImportFileCommand, ImportFileResult
from backend.application.use_cases.import_file import ImportFileUseCase
from backend.domain.enums import ImportSourceType


@dataclass(frozen=True, slots=True)
class ImportDataFile:
    name: str
    content: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportDataCommand:
    file: ImportDataFile
    source_type: ImportSourceType
    user_id: UUID


class ImportData:
    """APP-01 interface over the existing atomic Excel import use case."""

    def __init__(self, import_file: ImportFileUseCase) -> None:
        self._import_file = import_file

    def execute(self, command: ImportDataCommand) -> ImportFileResult:
        return self._import_file.execute(ImportFileCommand(
            source_type=command.source_type,
            file_name=command.file.name,
            content=command.file.content,
            imported_by=command.user_id,
        ))
