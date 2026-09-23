import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.application.dto.calculation import CalculationRunResult
from backend.domain.entities.enums import CalculationRunStatus
from backend.infrastructure.api.dependencies import get_uow, get_uow_factory
from backend.infrastructure.api.exceptions import ApiError
from backend.infrastructure.api.main import create_app
from backend.infrastructure.api.schemas.calculations import CalculationRunCreate, CalculationRunResponse
from backend.infrastructure.api.schemas.errors import ErrorResponse
from backend.infrastructure.api.schemas.orders import (
    ApproveOrderRequest, CreateOrdersRequest, OrderResponse,
)
from backend.infrastructure.api.schemas.recommendations import AdjustRecommendationRequest
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database


class ApiFoundationTests(unittest.TestCase):
    def setUp(self):
        self.database = Database("sqlite+pysqlite:///:memory:?check_same_thread=false")
        self.addCleanup(self.database.dispose)
        settings = Settings(
            database_url="postgresql+psycopg://test:unused@localhost:5432/test",
            cors_origins="http://frontend.test,http://localhost:3000",
            _env_file=None,
        )
        self.app = create_app(settings)

        @self.app.get("/test/invalid")
        def invalid(number: int):
            return {"number": number}

        @self.app.get("/test/http-error")
        def http_error():
            raise HTTPException(status_code=409, detail={"code": "conflict", "message": "Conflict"})

        @self.app.get("/test/api-error")
        def api_error():
            raise ApiError(409, "version_conflict", "Version changed")

        @self.app.get("/test/unexpected")
        def unexpected():
            raise ValueError("secret internal information")

        @self.app.get("/test/uow")
        def uow_probe(factory=Depends(get_uow_factory)):
            with factory() as uow:
                return {"configured": uow.imports is not None}

        @self.app.get("/test/uow-active")
        def active_uow_probe(uow=Depends(get_uow)):
            return {"configured": uow.imports is not None}

    def client(self):
        return patch("backend.infrastructure.api.main.Database", return_value=self.database)

    def test_health_cors_request_id_and_uow_dependency(self):
        with self.client(), TestClient(self.app) as client:
            supplied = str(uuid4())
            response = client.get(
                "/health", headers={"X-Request-ID": supplied, "Origin": "http://frontend.test"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["X-Request-ID"], supplied)
            self.assertEqual(response.headers["access-control-allow-origin"], "http://frontend.test")
            self.assertIn("X-Request-ID", response.headers["access-control-expose-headers"])
            self.assertEqual(client.get("/health/db").status_code, 200)
            self.assertEqual(client.get("/test/uow").json(), {"configured": True})
            self.assertEqual(client.get("/test/uow-active").json(), {"configured": True})
            denied = client.get("/health", headers={"Origin": "http://other.test"})
            self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_uniform_safe_errors(self):
        with self.client(), TestClient(self.app) as client:
            for path, status, code in (
                ("/test/invalid?number=no", 422, "request_validation_error"),
                ("/test/http-error", 409, "conflict"),
                ("/test/api-error", 409, "version_conflict"),
                ("/test/unexpected", 500, "internal_error"),
            ):
                response = client.get(path, headers={"X-Request-ID": "not-a-uuid"})
                self.assertEqual(response.status_code, status, response.text)
                parsed = ErrorResponse.model_validate(response.json())
                self.assertEqual(parsed.detail.code, code)
                self.assertEqual(str(UUID(parsed.request_id)), parsed.request_id)
                self.assertEqual(response.headers["X-Request-ID"], parsed.request_id)
                self.assertNotIn("secret internal information", response.text)
            self.assertEqual(
                client.get("/test/invalid?number=no").json()["detail"]["issues"][0]["loc"],
                ["query", "number"],
            )


class ApiSchemaTests(unittest.TestCase):
    def test_calculation_schema_matches_application_result(self):
        user_id = uuid4()
        command = CalculationRunCreate(user_id=user_id, horizon_days=30)
        self.assertEqual(command.user_id, user_id)
        with self.assertRaises(ValidationError):
            CalculationRunCreate(user_id=user_id, horizon_days=0)
        with self.assertRaises(ValidationError):
            CalculationRunCreate(user_id=user_id, horizon_days=30, unknown=True)
        result = CalculationRunResult(
            id=uuid4(), status=CalculationRunStatus.COMPLETED,
            parameters={"horizon_days": 30},
            started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc),
            algorithm_version="mvp-1", error_details=None,
            recommendation_count=2, import_batch_ids=(uuid4(),),
        )
        response = CalculationRunResponse.model_validate(result)
        self.assertEqual(response.recommendation_count, 2)
        self.assertEqual(len(response.import_batch_ids), 1)

    def test_adjustment_and_order_requests_are_strict(self):
        user_id = uuid4()
        request = AdjustRecommendationRequest(
            user_id=user_id, version=2, new_quantity=Decimal("12.5"), reason="  Seasonal correction  "
        )
        self.assertEqual(request.reason, "Seasonal correction")
        with self.assertRaises(ValidationError):
            AdjustRecommendationRequest(user_id=user_id, version=2, new_quantity=1, reason="  ")
        with self.assertRaises(ValidationError):
            AdjustRecommendationRequest(user_id=user_id, version=2, new_quantity=-1, reason="test")
        self.assertEqual(CreateOrdersRequest(user_id=user_id, calculation_run_id=uuid4()).recommendation_ids, None)
        self.assertEqual(ApproveOrderRequest(user_id=user_id).user_id, user_id)
        self.assertIn("items", OrderResponse.model_fields)
