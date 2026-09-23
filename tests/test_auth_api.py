"""Real bearer-token and role checks without an external PostgreSQL server."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.enums import UserRole
from backend.infrastructure.api.main import create_app
from backend.infrastructure.api import dependencies as deps
from backend.infrastructure.auth_security import hash_password
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.models import Base
from backend.infrastructure.persistence.models.catalog import UserCredentialModel, UserModel
from backend.domain.repositories.order_repository import OrderNotFoundError


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        with self.sessions.begin() as session:
            admin = UserModel(external_id="admin", display_name="Admin", role=UserRole.ADMIN)
            session.add(admin)
            session.flush()
            session.add(UserCredentialModel(user_id=admin.id, password_hash=hash_password("very-secure-admin-password")))
        self.settings = Settings(database_url="postgresql+psycopg://test:unused@localhost:5432/test",
                                 jwt_secret="a-random-test-only-secret-with-more-than-32-bytes",
                                 _env_file=None)
        self.app = create_app(self.settings)
        self.app.state.settings = self.settings
        self.app.state.database = SimpleNamespace(session=self.sessions.begin)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def login(self, username="admin", password="very-secure-admin-password"):
        return self.client.post("/api/auth/login", json={"username": username, "password": password})

    def test_admin_provisions_buyer_and_only_admin_can_approve(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.login(password="incorrect").status_code, 401)
        admin_token = self.login().json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        me = self.client.get("/api/auth/me", headers=admin_headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["role"], "admin")
        created = self.client.post("/api/auth/users", headers=admin_headers, json={
            "username": "Buyer.One", "display_name": "Buyer One", "password": "very-secure-buyer-password",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["role"], "buyer")
        self.assertEqual(self.client.post("/api/auth/users", headers=admin_headers, json={
            "username": "buyer.one", "display_name": "Duplicate", "password": "very-secure-buyer-password",
        }).status_code, 409)
        buyer_token = self.login("buyer.one", "very-secure-buyer-password").json()["access_token"]
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=buyer_headers).json()["role"], "buyer")
        self.assertEqual(self.client.post("/api/auth/users", headers=buyer_headers, json={
            "username": "other", "display_name": "Other", "password": "very-secure-buyer-password",
        }).status_code, 403)
        order_id = uuid4()
        order_url = f"/api/orders/{order_id}/approve"
        approve = Mock()
        approve.execute.side_effect = OrderNotFoundError(order_id)
        self.app.dependency_overrides[deps.get_approve_order] = lambda: approve
        self.assertEqual(self.client.post(order_url, headers=buyer_headers).status_code, 403)
        approve.execute.assert_not_called()
        self.assertEqual(self.client.post(order_url, headers=admin_headers).status_code, 404)

    def test_invalid_or_revoked_token_is_rejected(self):
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer malformed"}).status_code, 401)
        with self.sessions.begin() as session:
            session.query(UserCredentialModel).update({"token_version": 2})
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_disabled_account_cannot_use_live_token(self):
        token = self.login().json()["access_token"]
        with self.sessions.begin() as session:
            session.query(UserModel).filter_by(external_id="admin").update({"is_active": False})
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code, 401)
