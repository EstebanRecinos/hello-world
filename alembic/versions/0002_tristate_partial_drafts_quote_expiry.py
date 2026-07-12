"""tri-state safety answers, partial drafts, quote expiry/invalidation

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SAFETY_FIELDS = ("has_propulsion", "hazardous_materials", "needs_early_deploy", "itar_controlled")
PARTIAL_FIELDS = (
    ("mass_kg", sa.Float()),
    ("length_m", sa.Float()),
    ("width_m", sa.Float()),
    ("height_m", sa.Float()),
    ("target_orbit_name", sa.String(length=40)),
    ("target_inclination_deg", sa.Float()),
    ("target_altitude_km", sa.Float()),
)


def upgrade() -> None:
    # 1. Tri-state answer columns, backfilled from the booleans they replace.
    with op.batch_alter_table("payload_manifests") as batch:
        for field in SAFETY_FIELDS:
            batch.add_column(sa.Column(f"{field}_answer", sa.String(length=10), nullable=True))
    for field in SAFETY_FIELDS:
        op.execute(
            f"UPDATE payload_manifests SET {field}_answer = "
            f"CASE WHEN {field} THEN 'yes' ELSE 'no' END"
        )
    with op.batch_alter_table("payload_manifests") as batch:
        for field in SAFETY_FIELDS:
            batch.alter_column(f"{field}_answer", nullable=False)
            batch.drop_column(field)
        # 2. Partial drafts: wizard fields become nullable.
        for name, type_ in PARTIAL_FIELDS:
            batch.alter_column(name, existing_type=type_, nullable=True)

    # 3. Quote expiry and review-invalidation. Existing quotes: NULL = never
    # expires, keeping live data on its original terms.
    with op.batch_alter_table("quotes") as batch:
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("quotes") as batch:
        batch.drop_column("invalidated_at")
        batch.drop_column("expires_at")

    with op.batch_alter_table("payload_manifests") as batch:
        for field in SAFETY_FIELDS:
            batch.add_column(sa.Column(field, sa.Boolean(), nullable=True))
    for field in SAFETY_FIELDS:
        # Conservative: unsure downgrades to true.
        op.execute(
            f"UPDATE payload_manifests SET {field} = "
            f"CASE WHEN {field}_answer = 'no' THEN {_false()} ELSE {_true()} END"
        )
    # Partial drafts cannot survive the downgrade to NOT NULL: fill NULLs with
    # schema-level sentinels (0 / '') so the constraint can be restored.
    op.execute(
        "UPDATE payload_manifests SET "
        "mass_kg = COALESCE(mass_kg, 0), length_m = COALESCE(length_m, 0), "
        "width_m = COALESCE(width_m, 0), height_m = COALESCE(height_m, 0), "
        "target_orbit_name = COALESCE(target_orbit_name, ''), "
        "target_inclination_deg = COALESCE(target_inclination_deg, 0), "
        "target_altitude_km = COALESCE(target_altitude_km, 0)"
    )
    with op.batch_alter_table("payload_manifests") as batch:
        for field in SAFETY_FIELDS:
            batch.alter_column(field, nullable=False)
            batch.drop_column(f"{field}_answer")
        for name, type_ in PARTIAL_FIELDS:
            batch.alter_column(name, existing_type=type_, nullable=False)


def _true() -> str:
    return "TRUE" if op.get_bind().dialect.name == "postgresql" else "1"


def _false() -> str:
    return "FALSE" if op.get_bind().dialect.name == "postgresql" else "0"
