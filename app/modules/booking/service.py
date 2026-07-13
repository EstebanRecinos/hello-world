import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser
from app.config import get_settings
from app.domain.events import DomainEvent, event_bus
from app.domain.state_machine import ManifestState
from app.modules.booking.models import Booking, BookingStatus, Quote
from app.modules.booking.repository import BookingRepository
from app.modules.catalog.models import LaunchWindow, LaunchWindowStatus
from app.modules.manifests.models import PayloadManifest
from app.modules.manifests.service import IncompleteManifestError, ManifestService
from app.modules.pricing.engine import PricingEngine, get_pricing_engine
from app.utils import as_utc, utcnow

# States ops can drive through the generic advance endpoint. QUOTED, BOOKED
# and CANCELLED are reached through their own flows (quote/book/cancel), which
# carry side effects this endpoint must not bypass.
OPS_ADVANCE_STATES = frozenset(
    {
        ManifestState.INTEGRATED,
        ManifestState.LAUNCHED,
        ManifestState.DEPLOYED,
        ManifestState.CLOSED,
    }
)


class BookingError(Exception):
    """Domain-rule violation surfaced as HTTP 409."""


class QuoteNotFoundError(Exception):
    pass


class BookingService:
    def __init__(self, session: Session, pricer: PricingEngine | None = None) -> None:
        self.session = session
        self.repo = BookingRepository(session)
        self.manifests = ManifestService(session)
        self.pricer = pricer or get_pricing_engine()

    def _get_bookable_window(self, window_id: uuid.UUID, *, for_update: bool = False) -> LaunchWindow:
        window = self.session.get(
            LaunchWindow, window_id, with_for_update=for_update or None
        )
        if window is None:
            raise BookingError("Launch window not found")
        if window.status != LaunchWindowStatus.OPEN:
            raise BookingError("Launch window is not open for booking")
        if as_utc(window.launch_date) <= utcnow():
            raise BookingError("Launch window is in the past")
        return window

    def create_quote(
        self, manifest_id: uuid.UUID, launch_window_id: uuid.UUID, user: AuthenticatedUser
    ) -> Quote:
        manifest = self.manifests.get_for_user(manifest_id, user)
        if not manifest.is_complete:
            raise IncompleteManifestError(manifest.missing_fields)
        window = self._get_bookable_window(launch_window_id)

        ttl_hours = get_settings().quote_ttl_hours
        breakdown = self.pricer.quote(manifest, window)
        quote = Quote(
            manifest_id=manifest.id,
            launch_window_id=window.id,
            base_total_cents=breakdown.base_total_cents,
            multipliers=breakdown.multipliers,
            total_cents=breakdown.total_cents,
            expires_at=utcnow() + timedelta(hours=ttl_hours) if ttl_hours > 0 else None,
        )
        self.repo.add_quote(quote)
        self.session.flush()

        self.manifests.transition(
            manifest,
            ManifestState.QUOTED,
            actor=user.subject,
            event_type="manifest.quoted",
            data={
                "quote_id": str(quote.id),
                "launch_window_id": str(window.id),
                "price": breakdown.to_dict(),
            },
        )
        self.session.commit()
        return quote

    def book(
        self, manifest_id: uuid.UUID, quote_id: uuid.UUID, user: AuthenticatedUser
    ) -> Booking:
        manifest = self.manifests.get_for_user(manifest_id, user)
        quote = self.repo.get_quote(quote_id)
        if quote is None or quote.manifest_id != manifest.id:
            raise QuoteNotFoundError("Quote not found for this manifest")
        if quote.invalidated_at is not None:
            raise BookingError(
                "This quote was invalidated by a safety review; request a new quote"
            )
        if quote.expires_at is not None and as_utc(quote.expires_at) <= utcnow():
            # Persist the expiry event even though the booking fails.
            event_bus.publish(
                DomainEvent(
                    event_type="manifest.quote_expired",
                    actor=user.subject,
                    manifest_id=manifest.id,
                    data={"quote_id": str(quote.id), "expired_at": as_utc(quote.expires_at).isoformat()},
                ),
                self.session,
            )
            self.session.commit()
            raise BookingError("This quote has expired; request a new quote to see the current price")

        # Row lock (Postgres) so concurrent bookings can't oversell capacity.
        window = self._get_bookable_window(quote.launch_window_id, for_update=True)
        if window.remaining_kg < manifest.mass_kg or window.remaining_m3 < manifest.volume_m3:
            raise BookingError("Launch window no longer has capacity for this payload")

        self.manifests.transition(
            manifest,
            ManifestState.BOOKED,
            actor=user.subject,
            event_type="manifest.booked",
            data={
                "quote_id": str(quote.id),
                "launch_window_id": str(window.id),
                "total_cents": quote.total_cents,
            },
        )
        window.remaining_kg -= manifest.mass_kg
        window.remaining_m3 -= manifest.volume_m3

        booking = Booking(
            manifest_id=manifest.id,
            launch_window_id=window.id,
            quote_id=quote.id,
            total_cents=quote.total_cents,
        )
        self.repo.add_booking(booking)
        self.session.commit()
        return booking

    def cancel(self, manifest_id: uuid.UUID, user: AuthenticatedUser) -> PayloadManifest:
        manifest = self.manifests.get_for_user(manifest_id, user)
        released: dict | None = None

        booking = self.repo.get_active_booking_for_manifest(manifest.id)
        if booking is not None:
            window = self.session.get(LaunchWindow, booking.launch_window_id, with_for_update=True)
            if window is not None:
                window.remaining_kg += manifest.mass_kg
                window.remaining_m3 += manifest.volume_m3
            booking.status = BookingStatus.CANCELLED
            released = {"booking_id": str(booking.id), "launch_window_id": str(booking.launch_window_id)}

        self.manifests.transition(
            manifest,
            ManifestState.CANCELLED,
            actor=user.subject,
            event_type="manifest.cancelled",
            data={"released": released} if released else {},
        )
        self.session.commit()
        return manifest

    def advance(
        self, manifest_id: uuid.UUID, to_state: ManifestState, user: AuthenticatedUser
    ) -> PayloadManifest:
        """Ops-only lifecycle progression: integrated -> launched -> deployed -> closed."""
        if to_state not in OPS_ADVANCE_STATES:
            raise BookingError(
                f"State {to_state.value!r} cannot be set via advance; "
                "use the quote/book/cancel flows"
            )
        manifest = self.manifests.get_for_user(manifest_id, user)
        self.manifests.transition(manifest, to_state, actor=user.subject)
        self.session.commit()
        return manifest
