"""initial schema: launch_windows, payload_manifests, quotes, bookings, manifest_events

Revision ID: 0001
Revises:
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "launch_windows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("vehicle", sa.String(length=120), nullable=False),
        sa.Column("launch_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("orbit_name", sa.String(length=40), nullable=False),
        sa.Column("inclination_deg", sa.Float(), nullable=False),
        sa.Column("altitude_km", sa.Float(), nullable=False),
        sa.Column("capacity_kg", sa.Float(), nullable=False),
        sa.Column("capacity_m3", sa.Float(), nullable=False),
        sa.Column("remaining_kg", sa.Float(), nullable=False),
        sa.Column("remaining_m3", sa.Float(), nullable=False),
        sa.Column("base_price_cents_per_kg", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "payload_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("mass_kg", sa.Float(), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("target_orbit_name", sa.String(length=40), nullable=False),
        sa.Column("target_inclination_deg", sa.Float(), nullable=False),
        sa.Column("target_altitude_km", sa.Float(), nullable=False),
        sa.Column("has_propulsion", sa.Boolean(), nullable=False),
        sa.Column("hazardous_materials", sa.Boolean(), nullable=False),
        sa.Column("needs_early_deploy", sa.Boolean(), nullable=False),
        sa.Column("itar_controlled", sa.Boolean(), nullable=False),
        sa.Column("licensing_status", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tracking_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_token"),
    )
    op.create_index("ix_payload_manifests_customer_id", "payload_manifests", ["customer_id"])
    op.create_index("ix_payload_manifests_status", "payload_manifests", ["status"])
    op.create_index("ix_payload_manifests_tracking_token", "payload_manifests", ["tracking_token"])

    op.create_table(
        "quotes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("launch_window_id", sa.Uuid(), nullable=False),
        sa.Column("base_total_cents", sa.BigInteger(), nullable=False),
        sa.Column("multipliers", sa.JSON(), nullable=False),
        sa.Column("total_cents", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["payload_manifests.id"]),
        sa.ForeignKeyConstraint(["launch_window_id"], ["launch_windows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotes_manifest_id", "quotes", ["manifest_id"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("launch_window_id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("total_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["payload_manifests.id"]),
        sa.ForeignKeyConstraint(["launch_window_id"], ["launch_windows.id"]),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_id"),
    )

    # Append-only event log. No update/delete path exists in the app.
    op.create_table(
        "manifest_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("from_state", sa.String(length=20), nullable=True),
        sa.Column("to_state", sa.String(length=20), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["payload_manifests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manifest_events_manifest_id", "manifest_events", ["manifest_id"])


def downgrade() -> None:
    op.drop_table("manifest_events")
    op.drop_table("bookings")
    op.drop_table("quotes")
    op.drop_index("ix_payload_manifests_tracking_token", table_name="payload_manifests")
    op.drop_index("ix_payload_manifests_status", table_name="payload_manifests")
    op.drop_index("ix_payload_manifests_customer_id", table_name="payload_manifests")
    op.drop_table("payload_manifests")
    op.drop_table("launch_windows")
