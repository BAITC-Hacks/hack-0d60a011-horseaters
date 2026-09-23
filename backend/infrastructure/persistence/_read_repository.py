"""Read-only query execution and mapping shared by source repositories."""

from collections.abc import Collection
from dataclasses import fields
from datetime import date, datetime, timezone
from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select, or_, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from backend.domain.entities.base import Entity
from backend.domain.enums import ImportStatus
from backend.domain.repositories.filters import ALL, IdFilter
from .models.base import Base
from .models.imports import ImportBatchModel


EntityT = TypeVar("EntityT", bound=Entity)


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")
    return value.astimezone(timezone.utc)


def time_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    start, end = utc(start), utc(end)
    if end <= start:
        raise ValueError("end must be later than start")
    return start, end


def calendar_date(value: date) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError("A date without time is required")
    return value


def id_filter(column: ColumnElement, value: IdFilter) -> ColumnElement[bool]:
    return true() if value is ALL else column == value


def visible_import(column: ColumnElement, batch_ids: Collection[UUID] | None) -> ColumnElement[bool]:
    completed = select(ImportBatchModel.id).where(ImportBatchModel.status == ImportStatus.COMPLETED)
    if batch_ids is not None:
        return column.in_(completed.where(ImportBatchModel.id.in_(batch_ids)))
    # NULL is used by inferred/manual stockouts and growth assumptions.
    return or_(column.is_(None), column.in_(completed))


def to_entity(model: Base, entity_type: type[EntityT]) -> EntityT:
    values = {}
    for field in fields(entity_type):
        value = getattr(model, field.name)
        if isinstance(value, datetime):
            # SQLite demo loses tzinfo; stored timestamps follow the UTC contract.
            value = value.replace(tzinfo=timezone.utc) if value.utcoffset() is None else utc(value)
        values[field.name] = value
    return entity_type(**values)


class SqlAlchemyReadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _read(self, statement: Select, entity_type: type[EntityT]) -> list[EntityT]:
        # Even an externally supplied Session with autoflush=True must not write.
        with self.session.no_autoflush:
            return [to_entity(row, entity_type) for row in self.session.scalars(statement)]
