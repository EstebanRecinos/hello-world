from datetime import timedelta

from app.config import Settings
from app.modules.manifests.models import LicensingStatus
from app.modules.pricing.engine import V1MultiplierPricing
from app.utils import utcnow
from tests.conftest import make_manifest, make_window

SETTINGS = Settings(
    pricing_urgency_days_threshold=90,
    pricing_urgency_multiplier=1.25,
    pricing_atypical_volume_density_kg_m3=250,
    pricing_atypical_volume_multiplier=1.15,
    pricing_regulatory_risk_multiplier=1.20,
    _env_file=None,
)


def quote(manifest, window):
    return V1MultiplierPricing(SETTINGS).quote(manifest, window, now=utcnow())


def test_base_price_no_multipliers():
    # 100 kg, density 100/0.25 = 400 kg/m3 (not atypical), launch in 120 days, licensed.
    window = make_window(launch_date=utcnow() + timedelta(days=120))
    manifest = make_manifest()
    breakdown = quote(manifest, window)

    assert breakdown.base_total_cents == 650_000 * 100
    assert breakdown.multipliers == {}
    assert breakdown.total_cents == breakdown.base_total_cents
    assert isinstance(breakdown.total_cents, int)


def test_urgency_multiplier_applies_inside_threshold():
    window = make_window(launch_date=utcnow() + timedelta(days=30))
    breakdown = quote(make_manifest(), window)

    assert breakdown.multipliers == {"urgency": 1.25}
    assert breakdown.total_cents == round(breakdown.base_total_cents * 1.25)


def test_atypical_volume_multiplier_for_low_density():
    # 100 kg in 1 m3 = 100 kg/m3 < 250 threshold.
    window = make_window(launch_date=utcnow() + timedelta(days=120))
    manifest = make_manifest(length_m=2.0, width_m=1.0, height_m=0.5)
    breakdown = quote(manifest, window)

    assert breakdown.multipliers == {"atypical_volume": 1.15}


def test_regulatory_multiplier_for_hazardous_and_pending_license():
    window = make_window(launch_date=utcnow() + timedelta(days=120))

    hazardous = quote(make_manifest(hazardous_materials=True), window)
    assert hazardous.multipliers == {"regulatory_risk": 1.20}

    pending = quote(make_manifest(licensing_status=LicensingStatus.PENDING), window)
    assert pending.multipliers == {"regulatory_risk": 1.20}

    itar = quote(
        make_manifest(itar_controlled=True, licensing_status=LicensingStatus.NOT_REQUIRED),
        window,
    )
    assert itar.multipliers == {"regulatory_risk": 1.20}


def test_multipliers_compound_and_money_stays_integer():
    window = make_window(launch_date=utcnow() + timedelta(days=10))
    manifest = make_manifest(
        mass_kg=33.0,
        length_m=1.0, width_m=1.0, height_m=1.0,  # density 33 kg/m3
        hazardous_materials=True,
    )
    breakdown = quote(manifest, window)

    assert set(breakdown.multipliers) == {"urgency", "atypical_volume", "regulatory_risk"}
    expected = round(round(round(round(650_000 * 33.0) * 1.25) * 1.15) * 1.20)
    assert breakdown.total_cents == expected
    assert isinstance(breakdown.total_cents, int)
