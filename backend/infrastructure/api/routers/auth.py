"""Local employee login. Only an administrator can provision buyers."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.domain.entities.catalog import User
from backend.domain.enums import UserRole
from backend.infrastructure.api import dependencies as deps
from backend.infrastructure.api.schemas.auth import (
    CreateBuyerRequest, LoginRequest, StaffResponse, TokenResponse,
)
from backend.infrastructure.auth_security import hash_password, issue_access_token, verify_password
from backend.infrastructure.persistence.models.catalog import UserCredentialModel, UserModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _staff(account: UserModel | User) -> StaffResponse:
    return StaffResponse(id=account.id, username=account.external_id,
                         display_name=account.display_name, role=account.role)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    settings = request.app.state.settings
    if settings.jwt_secret is None:
        raise HTTPException(503, detail={"code": "auth_not_configured"})
    unauthorized = HTTPException(401, detail={"code": "invalid_credentials"},
                                 headers={"WWW-Authenticate": "Bearer"})
    with request.app.state.database.session() as session:
        account = session.scalar(select(UserModel).where(UserModel.external_id == body.username.strip().lower()))
        credentials = session.get(UserCredentialModel, account.id) if account else None
        if not account or not credentials or not account.is_active:
            raise unauthorized
        if not verify_password(credentials.password_hash, body.password):
            raise unauthorized
        token, lifetime = issue_access_token(account.id, credentials.token_version,
                                             settings.jwt_secret.get_secret_value(), settings.jwt_access_minutes)
    return TokenResponse(access_token=token, expires_in=lifetime)


@router.get("/me", response_model=StaffResponse)
def me(user: User = Depends(deps.get_current_user)) -> StaffResponse:
    return _staff(user)


@router.post("/users", response_model=StaffResponse, status_code=201)
def create_buyer(body: CreateBuyerRequest, request: Request,
                 _admin: User = Depends(deps.require_admin)) -> StaffResponse:
    account = UserModel(external_id=body.username.strip().lower(),
                        display_name=body.display_name.strip(), role=UserRole.BUYER)
    password_hash = hash_password(body.password)
    try:
        with request.app.state.database.session() as session:
            session.add(account)
            session.flush()
            session.add(UserCredentialModel(user_id=account.id, password_hash=password_hash))
            session.flush()
            result = _staff(account)
    except IntegrityError:
        raise HTTPException(409, detail={"code": "username_taken"}) from None
    return result
