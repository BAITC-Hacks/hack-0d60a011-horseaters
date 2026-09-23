import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.entities.imports import ImportBatch
from backend.domain.enums import ImportSourceType, ImportStatus, UserRole
from backend.domain.repositories.import_repository import (
    DuplicateImportError,
    ImportBatchNotFoundError,
    InvalidImportStatusTransitionError,
)
from backend.infrastructure.persistence.import_repository import (
    SqlAlchemyImportRepository,
)
from backend.infrastructure.persistence.models.base import Base
from backend.infrastructure.persistence.models.catalog import UserModel
from backend.infrastructure.persistence.models.imports import ImportBatchModel


class ImportRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(
            self.engine,
            tables=[UserModel.__table__, ImportBatchModel.__table__],
        )
        self.sessions = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.user_id = uuid4()
        with self.sessions.begin() as session:
            session.add(
                UserModel(
                    id=self.user_id,
                    external_id="buyer-1",
                    display_name="Buyer",
                    role=UserRole.BUYER,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )

    def batch(self, *, checksum: str = "a" * 64) -> ImportBatch:
        return ImportBatch(
            source_type=ImportSourceType.SALES,
            file_name="sales.xlsx",
            file_checksum=checksum,
            status=ImportStatus.PENDING,
            imported_by=self.user_id,
            imported_at=datetime.now(timezone.utc),
        )

    def repository(self, session: Session) -> SqlAlchemyImportRepository:
        return SqlAlchemyImportRepository(session)

    def test_create_and_get_batch_without_orm_leak(self):
        batch = self.batch()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            created = repository.create_batch(batch)
            loaded = repository.get(batch.id)

        self.assertEqual(created, batch)
        self.assertEqual(loaded, batch)
        self.assertIsInstance(loaded, ImportBatch)

    def test_processing_and_completed_transitions(self):
        batch = self.batch()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(batch)
            processing = repository.mark_processing(batch.id)
            completed = repository.mark_completed(batch.id, row_count=125)

        self.assertEqual(processing.status, ImportStatus.PROCESSING)
        self.assertEqual(completed.status, ImportStatus.COMPLETED)
        self.assertEqual(completed.row_count, 125)
        with self.sessions() as session:
            found = self.repository(session).get_completed_by_checksum(batch.file_checksum)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, batch.id)

    def test_failed_transition_preserves_structured_error(self):
        batch = self.batch()
        details = {"row": 17, "code": "invalid_quantity"}
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(batch)
            repository.mark_processing(batch.id)
            failed = repository.mark_failed(batch.id, error_details=details)

        self.assertEqual(failed.status, ImportStatus.FAILED)
        self.assertEqual(failed.error_details, details)

    def test_invalid_transition_is_rejected(self):
        batch = self.batch()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(batch)
            with self.assertRaises(InvalidImportStatusTransitionError):
                repository.mark_completed(batch.id, row_count=1)

    def test_missing_batch_has_domain_specific_error(self):
        missing_id = uuid4()
        with self.sessions() as session:
            with self.assertRaises(ImportBatchNotFoundError) as error:
                self.repository(session).mark_processing(missing_id)
        self.assertEqual(error.exception.batch_id, missing_id)

    def test_completed_checksum_cannot_be_imported_again(self):
        first = self.batch()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(first)
            repository.mark_processing(first.id)
            repository.mark_completed(first.id, row_count=1)

        second = self.batch()
        with self.sessions() as session:
            with self.assertRaises(DuplicateImportError):
                self.repository(session).create_batch(second)

    def test_failed_batch_does_not_block_retry(self):
        checksum = "b" * 64
        failed_batch = self.batch(checksum=checksum)
        retry = self.batch(checksum=checksum)
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(failed_batch)
            repository.mark_failed(failed_batch.id, error_details={"error": "bad file"})
            created_retry = repository.create_batch(retry)

        self.assertEqual(created_retry.status, ImportStatus.PENDING)

    def test_negative_row_count_is_rejected(self):
        batch = self.batch()
        with self.sessions.begin() as session:
            repository = self.repository(session)
            repository.create_batch(batch)
            repository.mark_processing(batch.id)
            with self.assertRaisesRegex(ValueError, "row_count"):
                repository.mark_completed(batch.id, row_count=-1)

    def test_repository_never_commits_its_own_transaction(self):
        batch = self.batch()
        session = self.sessions()
        try:
            self.repository(session).create_batch(batch)
            session.rollback()
        finally:
            session.close()

        with self.sessions() as verification_session:
            self.assertIsNone(self.repository(verification_session).get(batch.id))


if __name__ == "__main__":
    unittest.main()
