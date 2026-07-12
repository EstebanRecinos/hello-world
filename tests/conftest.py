import os

os.environ.setdefault("ORBITA_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ORBITA_JWT_SECRET", "test-secret")

from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.catalog.models import LaunchWindow  # noqa: E402
from app.modules.manifests.models import LicensingStatus, PayloadManifest  # noqa: E402
from app.utils import utcnow  # noqa: E402


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def client(session_factory):
    app = create_app()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def customer_headers(client):
    token = client.post(
        "/api/v1/auth/dev-token", json={"subject": "cust-1", "role": "customer"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_customer_headers(client):
    token = client.post(
        "/api/v1/auth/dev-token", json={"subject": "cust-2", "role": "customer"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ops_headers(client):
    token = client.post(
        "/api/v1/auth/dev-token", json={"subject": "ops-1", "role": "ops"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_window(**overrides) -> LaunchWindow:
    defaults = dict(
        provider="SpaceX",
        vehicle="Falcon 9",
        launch_date=utcnow() + timedelta(days=120),
        orbit_name="SSO",
        inclination_deg=97.6,
        altitude_km=550.0,
        capacity_kg=4000.0,
        capacity_m3=12.0,
        remaining_kg=4000.0,
        remaining_m3=12.0,
        base_price_cents_per_kg=650_000,
    )
    defaults.update(overrides)
    return LaunchWindow(**defaults)


def make_manifest(**overrides) -> PayloadManifest:
    defaults = dict(
        customer_id="cust-1",
        name="TestSat-1",
        mass_kg=100.0,
        length_m=1.0,
        width_m=0.5,
        height_m=0.5,
        target_orbit_name="SSO",
        target_inclination_deg=97.6,
        target_altitude_km=550.0,
        licensing_status=LicensingStatus.APPROVED,
    )
    defaults.update(overrides)
    return PayloadManifest(**defaults)
