import unittest
from datetime import datetime, timezone
from uuid import uuid4

from backend.application.dto.imports import ImportFileCommand, ParsedImport
from backend.application.use_cases.import_file import ImportFileUseCase, InvalidImportFileError
from backend.domain.entities.imports import ImportBatch
from backend.domain.enums import ImportSourceType, ImportStatus


class StubReader:
    def __init__(self, error=None):
        self.error = error

    def read(self, command):
        if self.error:
            raise self.error
        return ParsedImport(source_type=command.source_type, rows=({"row": 1},))


class StubGateway:
    def __init__(self):
        self.failed = None

    def start(self, command, *, checksum):
        self.checksum = checksum
        return ImportBatch(
            source_type=command.source_type,
            file_name=command.file_name,
            file_checksum=checksum,
            status=ImportStatus.PROCESSING,
            imported_by=command.imported_by,
            imported_at=datetime.now(timezone.utc),
        )

    def complete(self, batch, parsed):
        return ImportBatch(
            id=batch.id,
            source_type=batch.source_type,
            file_name=batch.file_name,
            file_checksum=batch.file_checksum,
            status=ImportStatus.COMPLETED,
            imported_by=batch.imported_by,
            imported_at=batch.imported_at,
            row_count=len(parsed.rows),
        )

    def fail(self, batch, *, error_details):
        self.failed = error_details
        return batch


class ImportFileUseCaseTests(unittest.TestCase):
    def command(self, *, content=b"xlsx"):
        return ImportFileCommand(
            source_type=ImportSourceType.SALES,
            file_name="sales.xlsx",
            content=content,
            imported_by=uuid4(),
        )

    def test_coordinates_checksum_parse_and_completion(self):
        gateway = StubGateway()
        result = ImportFileUseCase(StubReader(), gateway).execute(self.command())
        self.assertEqual(result.status, ImportStatus.COMPLETED)
        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.file_checksum, gateway.checksum)
        self.assertEqual(len(result.file_checksum), 64)

    def test_marks_started_batch_failed_when_reader_rejects_data(self):
        gateway = StubGateway()
        with self.assertRaisesRegex(ValueError, "broken"):
            ImportFileUseCase(StubReader(ValueError("broken")), gateway).execute(
                self.command()
            )
        self.assertEqual(gateway.failed["error_type"], "ValueError")

    def test_rejects_non_xlsx_empty_and_oversized_files_before_start(self):
        gateway = StubGateway()
        use_case = ImportFileUseCase(StubReader(), gateway, max_file_size=3)
        for name, content in (("sales.csv", b"a"), ("sales.xlsx", b""), ("sales.xlsx", b"1234")):
            with self.subTest(name=name, size=len(content)):
                with self.assertRaises(InvalidImportFileError):
                    use_case.execute(
                        ImportFileCommand(
                            source_type=ImportSourceType.SALES,
                            file_name=name,
                            content=content,
                            imported_by=uuid4(),
                        )
                    )


if __name__ == "__main__":
    unittest.main()
