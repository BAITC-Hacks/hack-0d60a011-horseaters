"""Check registration and the boundary between domain and persistence."""

import subprocess
import sys
import unittest
from dataclasses import fields
from pathlib import Path
from typing import get_args, get_type_hints

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.domain import entities
from backend.domain.entities import enums as calculation_enums
from backend.domain import enums as catalog_enums
from backend.infrastructure.persistence import models


CATALOG_AND_IMPORTS = (
    "User", "Category", "Product", "Warehouse", "Supplier", "SupplierProduct",
    "ImportBatch", "SalesTransaction", "MonthlySales", "InventorySnapshot",
    "StockoutPeriod", "InTransitItem", "SeasonalityCoefficient",
    "GrowthAssumption", "MaterialRequirement",
)


class ModelContractTests(unittest.TestCase):
    def test_package_import_registers_all_tables_in_fresh_process(self):
        script = (
            "from backend.infrastructure.persistence.models import Base; "
            "assert len(Base.metadata.tables) == 24, list(Base.metadata.tables); "
            "assert len(Base.metadata.sorted_tables) == 24"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_domain_fields_types_and_nullability_match_orm(self):
        for name in CATALOG_AND_IMPORTS:
            with self.subTest(entity=name):
                domain_class = getattr(entities, name)
                table = getattr(models, name + "Model").__table__
                self.assertEqual({field.name for field in fields(domain_class)}, set(table.c.keys()))
                hints = get_type_hints(domain_class)
                for column in table.c:
                    annotation = hints[column.name]
                    args = get_args(annotation)
                    self.assertEqual(type(None) in args, column.nullable, column.name)
                    actual = next((arg for arg in args if arg is not type(None)), annotation)
                    if hasattr(column.type, "enum_class"):
                        self.assertIs(actual, column.type.enum_class)
                    elif column.name != "error_details":
                        self.assertIs(actual, column.type.python_type)

    def test_orm_reuses_domain_enum_identity(self):
        from backend.infrastructure.persistence.models import enums as orm_enums

        for module in (catalog_enums, calculation_enums):
            for name, value in vars(module).items():
                if isinstance(value, type) and value.__module__ == module.__name__ and name != "StringEnum":
                    self.assertIs(getattr(orm_enums, name), value, name)

    def test_foreign_keys_and_ddl_for_both_dialects(self):
        configure_mappers()
        for table in models.Base.metadata.sorted_tables:
            for foreign_key in table.foreign_keys:
                self.assertIsNotNone(foreign_key.column)
            for dialect in (postgresql.dialect(), sqlite.dialect()):
                self.assertTrue(str(CreateTable(table).compile(dialect=dialect)))
                for index in table.indexes:
                    self.assertTrue(str(CreateIndex(index).compile(dialect=dialect)))

    def test_partial_unique_indexes_for_both_dialects(self):
        cases = (
            (models.ImportBatchModel, "status = 'completed'"),
            (models.SupplierProductModel, "is_active = true AND is_primary = true"),
        )
        for model, predicate in cases:
            index = next(index for index in model.__table__.indexes if index.unique)
            for dialect in (postgresql.dialect(), sqlite.dialect()):
                sql = str(CreateIndex(index).compile(dialect=dialect))
                self.assertIn("CREATE UNIQUE INDEX", sql)
                self.assertIn("WHERE " + predicate, sql)


if __name__ == "__main__":
    unittest.main()
