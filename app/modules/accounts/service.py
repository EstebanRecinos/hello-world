from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import Role, create_token
from app.config import get_settings
from app.domain.events import DomainEvent, event_bus
from app.email import send_email
from app.modules.accounts.hashing import (
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from app.modules.accounts.models import User
from app.utils import as_utc, utcnow


class AccountError(Exception):
    """Domain-rule violation; the router maps .status to an HTTP code."""

    def __init__(self, message: str, status: int = 409) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


class AccountService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ─── registration + verification ──────────────────────────────────────

    def register(self, email: str, display_name: str, password: str) -> User:
        existing = self.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise AccountError("That email is already registered. Try logging in.", 409)

        settings = get_settings()
        plain, token_hash = new_token()
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            verify_token_hash=token_hash,
            verify_expires_at=utcnow() + timedelta(hours=settings.account_verify_ttl_hours),
        )
        self.session.add(user)
        self.session.flush()
        self._emit("account.registered", user, {"email": email})
        self._send_verification(user, plain)
        self.session.commit()
        return user

    def verify(self, token: str) -> User:
        user = self._find_by(User.verify_token_hash, hash_token(token))
        if user is None:
            raise AccountError("This verification link is invalid or already used.", 400)
        if user.verify_expires_at is None or as_utc(user.verify_expires_at) <= utcnow():
            raise AccountError("This verification link has expired. Request a new one.", 400)
        user.email_verified = True
        user.verify_token_hash = None
        user.verify_expires_at = None
        self._emit("account.verified", user, {})
        self.session.commit()
        return user

    # ─── login with progressive lockout ───────────────────────────────────

    def login(self, email: str, password: str) -> str:
        user = self.session.scalar(select(User).where(User.email == email))
        # Uniform failure message so a wrong email and a wrong password are
        # indistinguishable (no account enumeration).
        invalid = AccountError("Email or password is incorrect.", 401)

        if user is None:
            raise invalid
        if user.locked_until is not None and as_utc(user.locked_until) > utcnow():
            raise AccountError(
                "Too many failed attempts. Try again in a few minutes.", 429
            )
        if not verify_password(password, user.password_hash):
            self._register_failed_login(user)
            self.session.commit()
            raise invalid
        if not user.email_verified:
            raise AccountError("Please verify your email before signing in.", 403)

        user.failed_logins = 0
        user.locked_until = None
        self._emit("account.login", user, {})
        self.session.commit()
        return create_token(str(user.id), Role(user.role))

    def _register_failed_login(self, user: User) -> None:
        settings = get_settings()
        user.failed_logins += 1
        data = {"failed_logins": user.failed_logins}
        if user.failed_logins >= settings.account_max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=settings.account_lockout_minutes)
            user.failed_logins = 0
            data["locked"] = True
        self._emit("account.login_failed", user, data)

    # ─── password reset ───────────────────────────────────────────────────

    def request_reset(self, email: str) -> None:
        """Always succeeds from the caller's view — never reveals whether the
        email exists."""
        user = self.session.scalar(select(User).where(User.email == email))
        if user is None:
            return
        settings = get_settings()
        plain, token_hash = new_token()
        user.reset_token_hash = token_hash
        user.reset_expires_at = utcnow() + timedelta(hours=settings.account_reset_ttl_hours)
        self._emit("account.reset_requested", user, {})
        self._send_reset(user, plain)
        self.session.commit()

    def reset(self, token: str, password: str) -> None:
        user = self._find_by(User.reset_token_hash, hash_token(token))
        if user is None:
            raise AccountError("This reset link is invalid or already used.", 400)
        if user.reset_expires_at is None or as_utc(user.reset_expires_at) <= utcnow():
            raise AccountError("This reset link has expired. Request a new one.", 400)
        user.password_hash = hash_password(password)
        user.reset_token_hash = None
        user.reset_expires_at = None
        # A successful reset clears any lockout.
        user.failed_logins = 0
        user.locked_until = None
        self._emit("account.reset_completed", user, {})
        self.session.commit()

    # ─── helpers ──────────────────────────────────────────────────────────

    def _find_by(self, column, value: str) -> User | None:
        return self.session.scalar(select(User).where(column == value))

    def _emit(self, event_type: str, user: User, data: dict) -> None:
        event_bus.publish(
            DomainEvent(event_type=event_type, actor=user.email, data=data),
            self.session,
        )

    def _send_verification(self, user: User, token: str) -> None:
        link = f"{get_settings().public_base_url}/#/verificar/{token}"
        send_email(
            user.email,
            "Confirma tu cuenta en ORBITA-LINK",
            f"Hola {user.display_name}:\n\n"
            f"Confirma tu cuenta para empezar a enviar carga al espacio:\n{link}\n\n"
            "Si no creaste esta cuenta, puedes ignorar este mensaje.",
        )

    def _send_reset(self, user: User, token: str) -> None:
        link = f"{get_settings().public_base_url}/#/nueva-contrasena/{token}"
        send_email(
            user.email,
            "Restablece tu contraseña de ORBITA-LINK",
            f"Hola {user.display_name}:\n\n"
            f"Para elegir una contraseña nueva, entra aquí:\n{link}\n\n"
            "Si no lo pediste, tu cuenta sigue segura y puedes ignorar este mensaje.",
        )
