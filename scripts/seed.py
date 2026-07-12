"""Seed the database with 3 launch windows and 5 example payload manifests.

Usage (after `alembic upgrade head`):
    python -m scripts.seed
Idempotent: skips seeding if any launch window already exists.
"""

from datetime import timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.modules.catalog.models import LaunchWindow
from app.modules.manifests.models import LicensingStatus, PayloadManifest
from app.utils import utcnow


def seed() -> None:
    session = SessionLocal()
    try:
        if session.scalar(select(LaunchWindow).limit(1)) is not None:
            print("Database already seeded; nothing to do.")
            return

        now = utcnow()

        windows = [
            LaunchWindow(
                provider="SpaceX",
                vehicle="Falcon 9 (Transporter-99)",
                launch_date=now + timedelta(days=120),
                orbit_name="SSO",
                inclination_deg=97.6,
                altitude_km=550,
                capacity_kg=4000,
                capacity_m3=12.0,
                remaining_kg=4000,
                remaining_m3=12.0,
                base_price_cents_per_kg=650_000,  # $6,500/kg
            ),
            LaunchWindow(
                provider="Rocket Lab",
                vehicle="Electron",
                launch_date=now + timedelta(days=60),
                orbit_name="SSO",
                inclination_deg=97.4,
                altitude_km=530,
                capacity_kg=300,
                capacity_m3=1.5,
                remaining_kg=300,
                remaining_m3=1.5,
                base_price_cents_per_kg=2_500_000,  # $25,000/kg — dedicated small launch
            ),
            LaunchWindow(
                provider="Arianespace",
                vehicle="Vega-C",
                launch_date=now + timedelta(days=200),
                orbit_name="LEO",
                inclination_deg=51.6,
                altitude_km=420,
                capacity_kg=2200,
                capacity_m3=8.0,
                remaining_kg=2200,
                remaining_m3=8.0,
                base_price_cents_per_kg=900_000,  # $9,000/kg
            ),
        ]
        session.add_all(windows)

        manifests = [
            PayloadManifest(
                customer_id="acme-earth-obs",
                name="AcmeSat-1 (Earth observation 6U)",
                mass_kg=12,
                length_m=0.36, width_m=0.24, height_m=0.12,
                target_orbit_name="SSO",
                target_inclination_deg=97.5,
                target_altitude_km=550,
                licensing_status=LicensingStatus.APPROVED,
            ),
            PayloadManifest(
                customer_id="acme-earth-obs",
                name="AcmeSat-2 (Earth observation 6U)",
                mass_kg=12,
                length_m=0.36, width_m=0.24, height_m=0.12,
                target_orbit_name="SSO",
                target_inclination_deg=97.5,
                target_altitude_km=540,
                licensing_status=LicensingStatus.PENDING,
            ),
            PayloadManifest(
                customer_id="orbital-iot",
                name="IoT-Relay-A (comms microsat)",
                mass_kg=85,
                length_m=0.8, width_m=0.6, height_m=0.5,
                target_orbit_name="LEO",
                target_inclination_deg=51.6,
                target_altitude_km=420,
                has_propulsion=True,
                licensing_status=LicensingStatus.APPROVED,
            ),
            PayloadManifest(
                customer_id="orbital-iot",
                name="IoT-Relay-B (comms microsat, early deploy)",
                mass_kg=85,
                length_m=0.8, width_m=0.6, height_m=0.5,
                target_orbit_name="LEO",
                target_inclination_deg=51.6,
                target_altitude_km=430,
                has_propulsion=True,
                # Customer wasn't sure about pressurized components: priced
                # conservatively and pending ops review (needs_review=true).
                hazardous_materials="unsure",
                needs_early_deploy=True,
                itar_controlled=True,
                licensing_status=LicensingStatus.PENDING,
            ),
            PayloadManifest(
                customer_id="uni-madrid-cubesats",
                name="Cubesat académico QubeX (3U)",
                mass_kg=4,
                length_m=0.34, width_m=0.1, height_m=0.1,
                target_orbit_name="SSO",
                target_inclination_deg=97.4,
                target_altitude_km=525,
                licensing_status=LicensingStatus.NOT_REQUIRED,
            ),
        ]
        session.add_all(manifests)
        session.commit()

        print(f"Seeded {len(windows)} launch windows and {len(manifests)} payload manifests.")
        for m in manifests:
            print(f"  {m.name}: tracking token = {m.tracking_token}")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
