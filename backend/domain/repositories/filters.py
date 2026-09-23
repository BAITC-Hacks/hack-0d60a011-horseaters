"""Explicit distinction between no filter and an SQL NULL value."""

from enum import Enum
from uuid import UUID


class AllValues(Enum):
    ALL = "all"


ALL = AllValues.ALL
IdFilter = UUID | None | AllValues


class AmbiguousSourceDataError(ValueError):
    """Several source records match and no documented rule selects a winner."""
