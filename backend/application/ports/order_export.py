from typing import Protocol, Sequence

from backend.application.dto.order import OrderExportRow


class OrderWorkbookExporter(Protocol):
    """Infrastructure port for rendering a stable 1C-compatible workbook."""

    def render(self, rows: Sequence[OrderExportRow]) -> bytes: ...
