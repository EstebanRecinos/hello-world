import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.booking.models import Booking, BookingStatus, Quote


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_quote(self, quote: Quote) -> Quote:
        self.session.add(quote)
        return quote

    def get_quote(self, quote_id: uuid.UUID) -> Quote | None:
        return self.session.get(Quote, quote_id)

    def add_booking(self, booking: Booking) -> Booking:
        self.session.add(booking)
        return booking

    def get_active_booking_for_manifest(self, manifest_id: uuid.UUID) -> Booking | None:
        return self.session.scalar(
            select(Booking).where(
                Booking.manifest_id == manifest_id,
                Booking.status == BookingStatus.ACTIVE,
            )
        )
