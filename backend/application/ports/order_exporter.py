from collections.abc import Sequence
from typing import Protocol

from backend.application.dto.order import OrderExportRow


class OrderExporter(Protocol):
    def render(self, rows: Sequence[OrderExportRow]) -> bytes:
        """Return the complete XLSX file, or raise without recording an export."""
        ...
