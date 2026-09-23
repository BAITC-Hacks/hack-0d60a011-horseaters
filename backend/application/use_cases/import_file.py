from __future__ import annotations

from hashlib import sha256

from backend.application.dto.imports import ImportFileCommand, ImportFileResult
from backend.application.ports.imports import ImportFileReader, ImportGateway

MAX_IMPORT_FILE_SIZE = 25 * 1024 * 1024


class ImportFileError(RuntimeError):
    pass


class InvalidImportFileError(ImportFileError):
    pass


class ImportFileUseCase:
    def __init__(
        self,
        reader: ImportFileReader,
        gateway: ImportGateway,
        *,
        max_file_size: int = MAX_IMPORT_FILE_SIZE,
    ) -> None:
        self._reader = reader
        self._gateway = gateway
        self._max_file_size = max_file_size

    def execute(self, command: ImportFileCommand) -> ImportFileResult:
        self._validate_command(command)
        checksum = sha256(command.content).hexdigest()
        batch = self._gateway.start(command, checksum=checksum)
        try:
            parsed = self._reader.read(command)
            completed = self._gateway.complete(batch, parsed)
        except Exception as error:
            details = {
                "error_type": type(error).__name__,
                "message": str(error) or "import failed",
            }
            if hasattr(error, "issues"):
                details["validation_errors"] = error.issues
            try:
                self._gateway.fail(batch, error_details=details)
                if hasattr(error, "issues"):
                    error.batch_id = batch.id
            except Exception as failure_error:
                error.add_note(
                    "Additionally failed to persist import failure status: "
                    f"{type(failure_error).__name__}"
                )
            raise
        return ImportFileResult(
            batch_id=completed.id,
            source_type=completed.source_type,
            status=completed.status,
            row_count=completed.row_count,
            file_checksum=completed.file_checksum,
        )

    def _validate_command(self, command: ImportFileCommand) -> None:
        name = command.file_name.strip()
        if not name:
            raise InvalidImportFileError("file_name must not be empty")
        if not name.lower().endswith(".xlsx"):
            raise InvalidImportFileError("only .xlsx files are supported")
        if not command.content:
            raise InvalidImportFileError("file must not be empty")
        if len(command.content) > self._max_file_size:
            raise InvalidImportFileError(
                f"file exceeds the {self._max_file_size}-byte limit"
            )
