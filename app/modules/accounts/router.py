from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.accounts.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RequestResetRequest,
    ResetRequest,
    TokenResponse,
    UserOut,
    VerifyRequest,
)
from app.modules.accounts.service import AccountError, AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(db)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, svc: AccountService = Depends(_service)) -> UserOut:
    try:
        user = svc.register(body.email, body.display_name, body.password)
    except AccountError as exc:
        raise HTTPException(exc.status, exc.message)
    return UserOut(
        id=str(user.id), email=user.email, display_name=user.display_name,
        role=user.role, email_verified=user.email_verified, created_at=user.created_at,
    )


@router.post("/verify", response_model=MessageResponse)
def verify(body: VerifyRequest, svc: AccountService = Depends(_service)) -> MessageResponse:
    try:
        svc.verify(body.token)
    except AccountError as exc:
        raise HTTPException(exc.status, exc.message)
    return MessageResponse(message="Tu cuenta quedó confirmada. Ya puedes iniciar sesión.")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, svc: AccountService = Depends(_service)) -> TokenResponse:
    try:
        return TokenResponse(access_token=svc.login(body.email, body.password))
    except AccountError as exc:
        raise HTTPException(exc.status, exc.message)


@router.post("/request-reset", response_model=MessageResponse)
def request_reset(
    body: RequestResetRequest, svc: AccountService = Depends(_service)
) -> MessageResponse:
    svc.request_reset(body.email)
    # Same response whether or not the email exists.
    return MessageResponse(
        message="Si esa dirección tiene una cuenta, te enviamos un enlace para restablecer tu contraseña."
    )


@router.post("/reset", response_model=MessageResponse)
def reset(body: ResetRequest, svc: AccountService = Depends(_service)) -> MessageResponse:
    try:
        svc.reset(body.token, body.password)
    except AccountError as exc:
        raise HTTPException(exc.status, exc.message)
    return MessageResponse(message="Tu contraseña quedó actualizada. Ya puedes iniciar sesión.")
