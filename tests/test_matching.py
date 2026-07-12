from app.config import Settings
from app.modules.matching.engine import V1ToleranceMatcher
from tests.conftest import make_manifest, make_window

SETTINGS = Settings(
    matching_inclination_tolerance_deg=1.5,
    matching_altitude_tolerance_km=50,
    _env_file=None,
)


def match(manifest, windows):
    return V1ToleranceMatcher(SETTINGS).match(manifest, windows)


def test_exact_orbit_scores_one():
    window = make_window(inclination_deg=97.6, altitude_km=550)
    manifest = make_manifest(target_inclination_deg=97.6, target_altitude_km=550)
    results = match(manifest, [window])

    assert len(results) == 1
    assert results[0].orbital_score == 1.0
    assert results[0].inclination_delta_deg == 0
    assert results[0].altitude_delta_km == 0


def test_window_outside_inclination_tolerance_is_excluded():
    window = make_window(inclination_deg=97.6)
    manifest = make_manifest(target_inclination_deg=99.5)  # delta 1.9 > 1.5
    assert match(manifest, [window]) == []


def test_window_outside_altitude_tolerance_is_excluded():
    window = make_window(altitude_km=550)
    manifest = make_manifest(target_altitude_km=620)  # delta 70 > 50
    assert match(manifest, [window]) == []


def test_window_without_mass_capacity_is_excluded():
    window = make_window(remaining_kg=50)
    manifest = make_manifest(mass_kg=100)
    assert match(manifest, [window]) == []


def test_window_without_volume_capacity_is_excluded():
    window = make_window(remaining_m3=0.1)
    manifest = make_manifest(length_m=1.0, width_m=1.0, height_m=1.0)
    assert match(manifest, [window]) == []


def test_closer_orbit_scores_higher():
    exact = make_window(inclination_deg=97.6, altitude_km=550)
    off = make_window(inclination_deg=98.5, altitude_km=580)
    manifest = make_manifest(target_inclination_deg=97.6, target_altitude_km=550)

    results = {id(r.window): r.orbital_score for r in match(manifest, [exact, off])}
    assert results[id(exact)] > results[id(off)]
