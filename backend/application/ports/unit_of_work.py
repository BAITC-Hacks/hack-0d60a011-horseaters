from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self


class Repository(Protocol):
    """Marker port refined by repository-specific protocols in REP tasks."""


class UnitOfWork(Protocol):
    """Application transaction boundary; contains no SQLAlchemy dependency."""

    @property
    def imports(self) -> Repository: ...

    @property
    def sales(self) -> Repository: ...

    @property
    def inventory(self) -> Repository: ...

    @property
    def suppliers(self) -> Repository: ...

    @property
    def calculation_runs(self) -> Repository: ...

    @property
    def recommendations(self) -> Repository: ...

    @property
    def orders(self) -> Repository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
