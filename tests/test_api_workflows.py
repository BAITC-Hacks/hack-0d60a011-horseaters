import hashlib
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.application.dto.calculation import CalculationRunResult
from backend.application.dto.imports import ImportFileResult
from backend.application.dto.order import ExportedOrder
from backend.application.use_cases.explain_recommendation import RecommendationExplanation
from backend.application.use_cases.list_recommendations import RecommendationPage
from backend.domain.entities.catalog import User
from backend.domain.entities.demand_forecast import DemandForecast
from backend.domain.entities.enums import CalculationRunStatus, ExportFormat, PurchaseOrderStatus, Urgency
from backend.domain.entities.order_export import OrderExport
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.entities.recommendation import Recommendation
from backend.domain.enums import ImportSourceType, ImportStatus, UserRole
from backend.domain.errors import InvalidEntityStateError
from backend.domain.repositories.order_repository import OrderNotFoundError
from backend.domain.repositories.recommendation_repository import RecommendationConflictError, RecommendationNotFoundError
from backend.domain.value_objects.demand import DemandSource
from backend.infrastructure.api import dependencies as deps
from backend.infrastructure.api.main import create_app
from backend.infrastructure.api.routers.orders import XLSX
from backend.infrastructure.excel.readers import ExcelImportValidationError


D = Decimal
NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)


class WorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.user = User(external_id="trusted", display_name="Buyer", role=UserRole.BUYER)

        @self.app.middleware("http")
        async def trusted_test_auth(request, call_next):
            # Represents a trusted identity adapter; never supplied by HTTP caller.
            request.state.user = self.user
            return await call_next(request)

        self.mocks = {}
        def override(value):
            def dependency():
                return value
            return dependency
        for name in ("import_data", "import_status", "run_calculation", "calculation_run", "list_recommendations",
                     "explain_recommendation", "adjust_recommendation", "create_orders", "order", "approve_order",
                     "export_order", "download_export"):
            use_case = Mock()
            self.mocks[name] = use_case
            self.app.dependency_overrides[getattr(deps, "get_" + name)] = override(use_case)
        # No lifespan or DB: each business operation is replaced at its dependency boundary.
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.run_id, self.product, self.warehouse, self.supplier = (uuid4() for _ in range(4))
        self.run = CalculationRunResult(
            id=self.run_id, status=CalculationRunStatus.COMPLETED,
            parameters={"horizon_days": 30, "demand_source": "transactions"}, started_at=NOW, finished_at=NOW,
            algorithm_version="mvp-1", error_details=None, recommendation_count=1, import_batch_ids=(),
        )
        self.rec = Recommendation(
            calculation_run_id=self.run_id, product_id=self.product, warehouse_id=self.warehouse,
            supplier_id=self.supplier, forecast_quantity=D(12), current_stock=D(0), in_transit_quantity=D(0),
            material_requirement_quantity=D(0), safety_stock=D(0), shortage_quantity=D(12),
            quantity_before_rounding=D(12), moq=D(1), package_size=D(1), recommended_quantity=D(12),
            effective_quantity=D(12), risk_score=D("0.5"), urgency=Urgency.MEDIUM, explanation="Saved explanation",
            calculation_details={"baseline": "12", "password": "hidden-secret"},
        )
        self.order = PurchaseOrder(order_number="PO-test", supplier_id=self.supplier, warehouse_id=self.warehouse,
                                   created_from_run_id=self.run_id, created_by=self.user.id, created_at=NOW)
        self.order.add_item(PurchaseOrderItem(recommendation_id=self.rec.id, product_id=self.product,
                                              recommended_quantity=D(12), approved_quantity=D(10)))
        self.mocks["calculation_run"].execute.return_value = self.run

    def upload(self, content=b"synthetic workbook", name="source.xlsx", **extra):
        return self.client.post("/api/imports", data={"source_type": "sales", **extra}, files={"file": (name, content, XLSX)})

    def test_import_passes_verified_actor_and_sanitized_filename(self):
        self.mocks["import_data"].execute.return_value = ImportFileResult(
            batch_id=uuid4(), source_type=ImportSourceType.SALES, status=ImportStatus.COMPLETED,
            row_count=2, file_checksum="a" * 64,
        )
        response = self.upload(name="private/path/source.xlsx", imported_by=str(uuid4()))
        self.assertEqual(response.status_code, 201, response.text)
        command = self.mocks["import_data"].execute.call_args.args[0]
        self.assertEqual(command.user_id, self.user.id)
        self.assertEqual(command.file.name, "source.xlsx")
        self.assertEqual(command.file.content, b"synthetic workbook")
        self.assertEqual(response.json()["row_count"], 2)

    def test_import_transport_validation_and_size_bound(self):
        self.assertEqual(self.upload(name="source.csv").status_code, 422)
        self.assertEqual(self.upload(content=b"").status_code, 422)
        with patch("backend.infrastructure.api.routers.imports.MAX_IMPORT_FILE_SIZE", 4):
            self.assertEqual(self.upload(content=b"12345").status_code, 422)
        response = self.client.post("/api/imports", data={"source_type": "unknown"}, files={"file": ("a.xlsx", b"x")})
        self.assertEqual(response.status_code, 422)
        self.mocks["import_data"].execute.assert_not_called()

    def test_import_errors_preserve_batch_and_hide_source_values(self):
        error = ExcelImportValidationError("C:/private/path secret", issues=[{"row": 4, "message": "Client email: secret@example.com"}])
        error.batch_id = uuid4()
        self.mocks["import_data"].execute.side_effect = error
        response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["import_batch_id"], str(error.batch_id))
        self.assertEqual(response.json()["detail"]["validation_errors"], [{"row": 4, "message": "invalid row values"}])
        self.assertNotIn("secret", response.text)

    def test_calculation_requires_explicit_source_and_forbids_audit_fields(self):
        for body in ({"horizon_days": 30}, {"horizon_days": 0, "demand_source": "transactions"},
                     {"horizon_days": 30, "demand_source": "auto"},
                     {"horizon_days": 30, "demand_source": "transactions", "user_id": str(uuid4())}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/calculation-runs", json=body).status_code, 422)
        self.mocks["run_calculation"].execute.assert_not_called()

    def test_calculation_post_passes_all_parameters_and_actor(self):
        self.mocks["run_calculation"].execute.return_value = self.run
        response = self.client.post("/api/calculation-runs", json={
            "horizon_days": 60, "demand_source": "monthly_sales", "warehouse_id": str(self.warehouse),
        })
        self.assertEqual(response.status_code, 201, response.text)
        command = self.mocks["run_calculation"].execute.call_args.args[0]
        self.assertEqual((command.horizon_days, command.demand_source, command.user_id), (60, DemandSource.MONTHLY_SALES, self.user.id))
        self.assertEqual(command.warehouse_id, self.warehouse)

    def test_failed_calculation_is_not_reported_as_success_and_details_are_safe(self):
        failed = replace(self.run, status=CalculationRunStatus.FAILED, error_details={"message": "postgresql://secret@private/db"})
        self.mocks["run_calculation"].execute.return_value = failed
        response = self.client.post("/api/calculation-runs", json={"horizon_days": 30, "demand_source": "transactions"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("secret", response.text)
        self.mocks["calculation_run"].execute.return_value = failed
        response = self.client.get(f"/api/calculation-runs/{self.run_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error_details"], {"code": "calculation_failed"})

    def test_list_pagination_and_existing_filters(self):
        self.mocks["list_recommendations"].execute.return_value = RecommendationPage([self.rec], 90, 2, 4)
        response = self.client.get(f"/api/calculation-runs/{self.run_id}/recommendations", params={
            "limit": 2, "offset": 4, "supplier_id": str(self.supplier), "warehouse_id": str(self.warehouse),
            "urgency": "medium", "status": "suggested", "sort_by": "recommended_quantity", "descending": "false",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((response.json()["total"], response.json()["offset"]), (90, 4))
        query = self.mocks["list_recommendations"].execute.call_args.args[0]
        self.assertEqual((query.limit, query.offset, query.supplier_id, query.descending), (2, 4, self.supplier, False))
        self.assertNotIn("hidden-secret", response.text)
        for params in ({"limit": 501}, {"limit": 0}, {"offset": -1}, {"sort_by": "raw_sql"}):
            self.assertEqual(self.client.get(f"/api/calculation-runs/{self.run_id}/recommendations", params=params).status_code, 422)

    def test_explanation_uses_saved_result_only(self):
        forecast = DemandForecast(calculation_run_id=self.run_id, product_id=self.product, warehouse_id=self.warehouse,
                                  period_start=date(2026, 9, 1), period_end=date(2026, 9, 30), raw_demand=D(12),
                                  return_adjustment=D(0), anomaly_adjustment=D(0), stockout_adjustment=D(0),
                                  cleaned_baseline=D(12), growth_rate=D(0), seasonality_index=D(1), forecast_quantity=D(12),
                                  details={"customer_name": "secret"})
        self.mocks["explain_recommendation"].execute.return_value = RecommendationExplanation(
            self.rec.id, "saved formula", {"baseline": "12", "customer_name": "secret"}, [], forecast, "Saved explanation",
        )
        response = self.client.get(f"/api/recommendations/{self.rec.id}/explain")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["forecast"]["period_start"], "2026-09-01")
        self.assertNotIn("secret", response.text)
        self.mocks["run_calculation"].execute.assert_not_called()

    def test_adjustment_passes_version_reason_quantity_and_actor(self):
        self.mocks["adjust_recommendation"].execute.return_value = self.rec
        response = self.client.patch(f"/api/recommendations/{self.rec.id}", json={
            "new_quantity": "12.1234", "version": 3, "reason": "  planned need  ",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.mocks["adjust_recommendation"].execute.assert_called_once_with(
            self.rec.id, expected_version=3, new_quantity=D("12.1234"), reason="planned need", user_id=self.user.id,
        )
        for changes in ({"new_quantity": "-1"}, {"new_quantity": "NaN"}, {"new_quantity": "1.00001"},
                        {"reason": " "}, {"version": 0}, {"approved_by": str(uuid4())}):
            body = {"new_quantity": "12", "version": 3, "reason": "reason", **changes}
            self.assertEqual(self.client.patch(f"/api/recommendations/{self.rec.id}", json=body).status_code, 422)

    def test_not_found_and_conflict_mapping(self):
        path = f"/api/recommendations/{self.rec.id}"
        for error, status in ((RecommendationConflictError("secret"), 409), (InvalidEntityStateError("secret"), 409),
                              (RecommendationNotFoundError("secret"), 404), (PermissionError("secret"), 403)):
            self.mocks["adjust_recommendation"].execute.side_effect = error
            response = self.client.patch(path, json={"new_quantity": "1", "version": 1, "reason": "why"})
            self.assertEqual(response.status_code, status)
            self.assertNotIn("secret", response.text)
        self.mocks["calculation_run"].execute.return_value = None
        self.assertEqual(self.client.get(f"/api/calculation-runs/{uuid4()}").status_code, 404)
        self.mocks["explain_recommendation"].execute.return_value = None
        self.assertEqual(self.client.get(f"/api/recommendations/{uuid4()}/explain").status_code, 404)
        self.mocks["order"].execute.side_effect = OrderNotFoundError(uuid4())
        self.assertEqual(self.client.get(f"/api/orders/{uuid4()}").status_code, 404)

    def test_order_creation_read_and_approval_use_cases(self):
        self.mocks["create_orders"].execute.return_value = (self.order,)
        self.mocks["order"].execute.return_value = self.order
        response = self.client.post("/api/orders", json={"calculation_run_id": str(self.run_id)})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()[0]["status"], "draft")
        self.mocks["create_orders"].execute.assert_called_once_with(self.run_id, user_id=self.user.id)
        self.assertEqual(self.client.get(f"/api/orders/{self.order.id}").json()["items"][0]["approved_quantity"], "10")
        self.order.approve(approved_by=self.user.id)
        self.mocks["approve_order"].execute.return_value = self.order
        self.assertEqual(self.client.post(f"/api/orders/{self.order.id}/approve").status_code, 200)
        self.mocks["approve_order"].execute.assert_called_once_with(self.order.id, user_id=self.user.id)
        self.assertEqual(self.client.post(f"/api/orders/{self.order.id}/approve", json={"approved_by": str(uuid4())}).status_code, 422)

    def test_unknown_run_does_not_create_orders(self):
        self.mocks["calculation_run"].execute.return_value = None
        self.assertEqual(self.client.post("/api/orders", json={"calculation_run_id": str(uuid4())}).status_code, 404)
        self.mocks["create_orders"].execute.assert_not_called()

    def test_export_post_creates_and_get_only_downloads(self):
        content = b"PK-synthetic-xlsx-bytes"
        metadata = OrderExport(purchase_order_id=self.order.id, format=ExportFormat.XLSX,
                               file_name="order.xlsx", file_checksum=hashlib.sha256(content).hexdigest(), created_by=self.user.id)
        result = ExportedOrder(metadata=metadata, content=content)
        self.mocks["export_order"].execute.return_value = result
        self.mocks["download_export"].execute.return_value = result
        post = self.client.post(f"/api/orders/{self.order.id}/export")
        self.assertEqual(post.status_code, 201, post.text)
        self.assertEqual(post.json()["file_checksum"], metadata.file_checksum)
        self.mocks["export_order"].execute.assert_called_once_with(self.order.id, user_id=self.user.id)
        self.mocks["export_order"].execute.reset_mock()
        self.user = replace(self.user, role=UserRole.VIEWER)
        for _ in range(2):
            response = self.client.get(f"/api/orders/{self.order.id}/export")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, content)
            self.assertEqual(response.headers["content-type"], XLSX)
            self.assertIn(f'filename="order-{self.order.id}.xlsx"', response.headers["content-disposition"])
        self.mocks["export_order"].execute.assert_not_called()

    def test_export_status_conflict_and_no_file_yet(self):
        self.mocks["export_order"].execute.side_effect = InvalidEntityStateError("approved required")
        self.assertEqual(self.client.post(f"/api/orders/{self.order.id}/export").status_code, 409)
        self.mocks["download_export"].execute.side_effect = LookupError("not exported")
        self.assertEqual(self.client.get(f"/api/orders/{self.order.id}/export").status_code, 404)

    def test_viewer_cannot_mutate_and_absent_user_cannot_read(self):
        self.user = replace(self.user, role=UserRole.VIEWER)
        responses = [self.upload(), self.client.post("/api/calculation-runs", json={"demand_source": "transactions", "horizon_days": 30}),
                     self.client.patch(f"/api/recommendations/{self.rec.id}", json={"new_quantity": "1", "version": 1, "reason": "why"}),
                     self.client.post("/api/orders", json={"calculation_run_id": str(self.run_id)}),
                     self.client.post(f"/api/orders/{self.order.id}/approve"), self.client.post(f"/api/orders/{self.order.id}/export")]
        self.assertTrue(all(response.status_code == 403 for response in responses))
        self.user = None
        response = self.client.get(f"/api/orders/{self.order.id}", headers={"X-User-ID": str(uuid4())})
        self.assertEqual(response.status_code, 403)
        self.user = User(external_id="disabled", display_name="Disabled", role=UserRole.ADMIN, is_active=False)
        self.assertEqual(self.client.get(f"/api/orders/{self.order.id}").status_code, 403)

    def test_internal_and_database_errors_never_leak_diagnostics(self):
        for error, status in ((RuntimeError("secret C:/private/file"), 500),
                              (KeyError("secret"), 500), (OperationalError("password=secret", {}, None), 503)):
            self.mocks["order"].execute.side_effect = error
            response = self.client.get(f"/api/orders/{self.order.id}")
            self.assertEqual(response.status_code, status, response.text)
            self.assertNotIn("secret", response.text)
            self.assertEqual(response.json()["request_id"], response.headers["X-Request-ID"])
            self.assertIn("message", response.json()["detail"])
        response = self.client.post("/api/calculation-runs", json={"password": "secret"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("secret", response.text)

    def test_openapi_lists_binary_get_and_separate_export_command(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(set(schema["paths"]["/api/orders/{order_id}/export"]), {"get", "post"})
        self.assertIn(XLSX, schema["paths"]["/api/orders/{order_id}/export"]["get"]["responses"]["200"]["content"])


if __name__ == "__main__":
    unittest.main()
