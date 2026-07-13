"""End-to-end coverage of the three UX-driven backend changes:
1. Tri-state safety answers ('unsure') + ops review that invalidates quotes.
2. Partial drafts: only name required; completeness enforced when quoting.
3. Quote expiry."""

from datetime import timedelta

from app.utils import utcnow
from tests.test_booking_flow import MANIFEST, create_manifest, create_window


# ─── Friction 1: tri-state + review ───────────────────────────────────────


def test_booleans_still_accepted_and_reflected(client, customer_headers):
    m = create_manifest(client, customer_headers)  # uses booleans-free defaults
    assert m["has_propulsion"] is False
    assert m["has_propulsion_answer"] == "no"

    m2 = create_manifest(client, customer_headers, name="Bool-Sat", hazardous_materials=True)
    assert m2["hazardous_materials"] is True
    assert m2["hazardous_materials_answer"] == "yes"
    assert m2["needs_review"] is False


def test_unsure_flags_review_and_derives_conservatively(client, customer_headers):
    m = create_manifest(
        client, customer_headers, name="Unsure-Sat", hazardous_materials="unsure"
    )
    assert m["hazardous_materials_answer"] == "unsure"
    assert m["hazardous_materials"] is True  # conservative
    assert m["needs_review"] is True
    assert m["unsure_fields"] == ["hazardous_materials"]

    events = client.get(
        f"/api/v1/manifests/{m['id']}/events", headers=customer_headers
    ).json()
    assert any(e["event_type"] == "manifest.review_requested" for e in events)


def test_unsure_prices_conservatively(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    m = create_manifest(
        client, customer_headers, name="Unsure-Priced",
        hazardous_materials="unsure", licensing_status="approved",
    )
    quote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    assert quote["multipliers"] == {"regulatory_risk": 1.2}


def test_review_requires_ops_and_unsure_fields(client, customer_headers, ops_headers):
    m = create_manifest(client, customer_headers, name="R1", hazardous_materials="unsure")

    denied = client.post(
        f"/api/v1/manifests/{m['id']}/review",
        json={"resolutions": {"hazardous_materials": "no"}},
        headers=customer_headers,
    )
    assert denied.status_code == 403

    wrong_field = client.post(
        f"/api/v1/manifests/{m['id']}/review",
        json={"resolutions": {"has_propulsion": "no"}},
        headers=ops_headers,
    )
    assert wrong_field.status_code == 409
    assert "not marked unsure" in wrong_field.json()["detail"]


def test_review_on_quoted_invalidates_quote_and_lowers_price(
    client, customer_headers, ops_headers
):
    window = create_window(client, ops_headers)
    m = create_manifest(
        client, customer_headers, name="R2",
        hazardous_materials="unsure", licensing_status="approved",
    )
    mid = m["id"]

    quote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    assert quote["multipliers"] == {"regulatory_risk": 1.2}

    reviewed = client.post(
        f"/api/v1/manifests/{mid}/review",
        json={"resolutions": {"hazardous_materials": "no"}},
        headers=ops_headers,
    )
    assert reviewed.status_code == 200
    body = reviewed.json()
    assert body["needs_review"] is False
    assert body["hazardous_materials"] is False
    assert body["status"] == "quoted"  # state untouched

    # The old quote is now invalidated: booking it fails explicitly.
    blocked = client.post(
        f"/api/v1/manifests/{mid}/book",
        json={"quote_id": quote["id"]},
        headers=customer_headers,
    )
    assert blocked.status_code == 409
    assert "invalidated" in blocked.json()["detail"]

    # Re-quoting (quoted -> quoted) yields the lower, multiplier-free price.
    requote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    assert requote["multipliers"] == {}
    assert requote["total_cents"] < quote["total_cents"]

    ok = client.post(
        f"/api/v1/manifests/{mid}/book",
        json={"quote_id": requote["id"]},
        headers=customer_headers,
    )
    assert ok.status_code == 201

    events = client.get(f"/api/v1/manifests/{mid}/events", headers=ops_headers).json()
    resolved = [e for e in events if e["event_type"] == "manifest.review_resolved"]
    assert len(resolved) == 1
    assert resolved[0]["data"]["resolutions"] == {"hazardous_materials": "no"}
    assert resolved[0]["data"]["invalidated_quotes"] == [quote["id"]]


def test_review_rejected_after_booking(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    m = create_manifest(client, customer_headers, name="R3", has_propulsion="unsure")
    mid = m["id"]
    quote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    client.post(f"/api/v1/manifests/{mid}/book", json={"quote_id": quote["id"]}, headers=customer_headers)

    resp = client.post(
        f"/api/v1/manifests/{mid}/review",
        json={"resolutions": {"has_propulsion": "no"}},
        headers=ops_headers,
    )
    assert resp.status_code == 409


# ─── Friction 2: partial drafts ───────────────────────────────────────────


def test_draft_with_only_name(client, customer_headers):
    resp = client.post("/api/v1/manifests", json={"name": "Solo nombre"}, headers=customer_headers)
    assert resp.status_code == 201, resp.text
    m = resp.json()
    assert m["status"] == "draft"
    assert m["is_complete"] is False
    assert set(m["missing_fields"]) == {
        "mass_kg", "length_m", "width_m", "height_m",
        "target_orbit_name", "target_inclination_deg", "target_altitude_km",
    }
    assert m["volume_m3"] is None


def test_incomplete_manifest_cannot_quote_or_match(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    m = client.post(
        "/api/v1/manifests", json={"name": "Parcial", "mass_kg": 10}, headers=customer_headers
    ).json()

    quote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    )
    assert quote.status_code == 409
    detail = quote.json()["detail"]
    assert "mass_kg" not in detail["missing_fields"]
    assert "target_orbit_name" in detail["missing_fields"]

    matches = client.get(f"/api/v1/manifests/{m['id']}/matches", headers=customer_headers)
    assert matches.status_code == 409
    assert "missing_fields" in matches.json()["detail"]


def test_completing_a_partial_draft_unlocks_quoting(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    m = client.post("/api/v1/manifests", json={"name": "Progresivo"}, headers=customer_headers).json()

    fill = {k: v for k, v in MANIFEST.items() if k != "name"}
    updated = client.patch(f"/api/v1/manifests/{m['id']}", json=fill, headers=customer_headers).json()
    assert updated["is_complete"] is True
    assert updated["missing_fields"] == []

    quote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    )
    assert quote.status_code == 201


# ─── Friction 3: quote expiry ─────────────────────────────────────────────


def test_quote_gets_expiry_from_config(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    m = create_manifest(client, customer_headers, name="TTL-Sat")
    quote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    assert quote["expires_at"] is not None
    assert quote["invalidated_at"] is None


def test_expired_quote_cannot_be_booked(client, customer_headers, ops_headers, session_factory):
    import uuid as uuid_mod

    from app.modules.booking.models import Quote

    window = create_window(client, ops_headers)
    m = create_manifest(client, customer_headers, name="Expired-Sat")
    quote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()

    # Age the quote past its TTL directly in the database.
    session = session_factory()
    db_quote = session.get(Quote, uuid_mod.UUID(quote["id"]))
    db_quote.expires_at = utcnow() - timedelta(hours=1)
    session.commit()
    session.close()

    blocked = client.post(
        f"/api/v1/manifests/{m['id']}/book",
        json={"quote_id": quote["id"]},
        headers=customer_headers,
    )
    assert blocked.status_code == 409
    assert "expired" in blocked.json()["detail"]

    events = client.get(f"/api/v1/manifests/{m['id']}/events", headers=customer_headers).json()
    expired = [e for e in events if e["event_type"] == "manifest.quote_expired"]
    assert len(expired) == 1
    assert expired[0]["data"]["quote_id"] == quote["id"]

    # Re-quote and book: the recovery path works.
    requote = client.post(
        f"/api/v1/manifests/{m['id']}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    ok = client.post(
        f"/api/v1/manifests/{m['id']}/book",
        json={"quote_id": requote["id"]},
        headers=customer_headers,
    )
    assert ok.status_code == 201
