"""End-to-end flow through the API: catalog -> manifest -> matching -> quote
-> booking -> lifecycle -> tracking. Also covers auth boundaries and invalid
state transitions."""

from datetime import datetime, timedelta, timezone


def iso_in(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


WINDOW = {
    "provider": "SpaceX",
    "vehicle": "Falcon 9 (Transporter)",
    "orbit_name": "SSO",
    "inclination_deg": 97.6,
    "altitude_km": 550,
    "capacity_kg": 4000,
    "capacity_m3": 12.0,
    "base_price_cents_per_kg": 650000,
}

MANIFEST = {
    "name": "TestSat-1",
    "mass_kg": 100,
    "length_m": 1.0,
    "width_m": 0.5,
    "height_m": 0.5,
    "target_orbit_name": "SSO",
    "target_inclination_deg": 97.6,
    "target_altitude_km": 550,
    "licensing_status": "approved",
}


def create_window(client, ops_headers, **overrides):
    body = {**WINDOW, "launch_date": iso_in(120), **overrides}
    resp = client.post("/api/v1/launches", json=body, headers=ops_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_manifest(client, headers, **overrides):
    resp = client.post("/api/v1/manifests", json={**MANIFEST, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_full_happy_path(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    manifest = create_manifest(client, customer_headers)
    assert manifest["status"] == "draft"
    mid = manifest["id"]

    # Matching returns the compatible window with an estimated price.
    matches = client.get(f"/api/v1/manifests/{mid}/matches", headers=customer_headers).json()
    assert len(matches) == 1
    assert matches[0]["launch_window"]["id"] == window["id"]
    assert matches[0]["orbital_score"] == 1.0
    assert matches[0]["estimated_price"]["total_cents"] == 650000 * 100

    # Quote: draft -> quoted.
    quote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    assert quote["total_cents"] == 650000 * 100
    assert client.get(f"/api/v1/manifests/{mid}", headers=customer_headers).json()["status"] == "quoted"

    # Book: quoted -> booked, capacity decremented.
    booking = client.post(
        f"/api/v1/manifests/{mid}/book",
        json={"quote_id": quote["id"]},
        headers=customer_headers,
    )
    assert booking.status_code == 201, booking.text
    window_after = client.get(f"/api/v1/launches/{window['id']}", headers=customer_headers).json()
    assert window_after["remaining_kg"] == 3900
    assert window_after["remaining_m3"] == 11.75

    # Ops advances the lifecycle to closed.
    for state in ["integrated", "launched", "deployed", "closed"]:
        resp = client.post(
            f"/api/v1/manifests/{mid}/status", json={"to_state": state}, headers=ops_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == state

    # Public tracking: full history via token, no auth header.
    tracking = client.get(f"/api/v1/tracking/{manifest['tracking_token']}")
    assert tracking.status_code == 200
    body = tracking.json()
    assert body["status"] == "closed"
    event_types = [e["event_type"] for e in body["history"]]
    assert event_types[0] == "manifest.created"
    assert "manifest.quoted" in event_types
    assert "manifest.booked" in event_types
    assert event_types.count("manifest.state_changed") == 4


def test_booking_without_quote_state_fails_explicitly(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    manifest = create_manifest(client, customer_headers)

    # Try to advance a draft manifest straight to integrated.
    resp = client.post(
        f"/api/v1/manifests/{manifest['id']}/status",
        json={"to_state": "integrated"},
        headers=ops_headers,
    )
    assert resp.status_code == 409
    assert "draft" in resp.json()["detail"] and "integrated" in resp.json()["detail"]


def test_cancel_restores_capacity_and_blocks_further_transitions(
    client, customer_headers, ops_headers
):
    window = create_window(client, ops_headers)
    manifest = create_manifest(client, customer_headers)
    mid = manifest["id"]

    quote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    client.post(f"/api/v1/manifests/{mid}/book", json={"quote_id": quote['id']}, headers=customer_headers)

    resp = client.post(f"/api/v1/manifests/{mid}/cancel", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    window_after = client.get(f"/api/v1/launches/{window['id']}", headers=customer_headers).json()
    assert window_after["remaining_kg"] == 4000  # capacity released

    # Terminal state: nothing moves anymore.
    resp = client.post(
        f"/api/v1/manifests/{mid}/status", json={"to_state": "integrated"}, headers=ops_headers
    )
    assert resp.status_code == 409


def test_cancel_rejected_after_integration(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    manifest = create_manifest(client, customer_headers)
    mid = manifest["id"]

    quote = client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    ).json()
    client.post(f"/api/v1/manifests/{mid}/book", json={"quote_id": quote['id']}, headers=customer_headers)
    client.post(f"/api/v1/manifests/{mid}/status", json={"to_state": "integrated"}, headers=ops_headers)

    resp = client.post(f"/api/v1/manifests/{mid}/cancel", headers=customer_headers)
    assert resp.status_code == 409


def test_booking_fails_when_capacity_exhausted(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers, capacity_kg=150)
    first = create_manifest(client, customer_headers)
    second = create_manifest(client, customer_headers, name="TestSat-2")

    for manifest in (first, second):
        quote = client.post(
            f"/api/v1/manifests/{manifest['id']}/quotes",
            json={"launch_window_id": window["id"]},
            headers=customer_headers,
        ).json()
        manifest["quote_id"] = quote["id"]

    ok = client.post(
        f"/api/v1/manifests/{first['id']}/book",
        json={"quote_id": first["quote_id"]},
        headers=customer_headers,
    )
    assert ok.status_code == 201

    # Only 50 kg left; second payload needs 100 kg.
    overbooked = client.post(
        f"/api/v1/manifests/{second['id']}/book",
        json={"quote_id": second["quote_id"]},
        headers=customer_headers,
    )
    assert overbooked.status_code == 409
    assert "capacity" in overbooked.json()["detail"]


def test_customers_cannot_see_each_others_manifests(
    client, customer_headers, other_customer_headers, ops_headers
):
    manifest = create_manifest(client, customer_headers)

    resp = client.get(f"/api/v1/manifests/{manifest['id']}", headers=other_customer_headers)
    assert resp.status_code == 404  # not 403: existence is not leaked

    listing = client.get("/api/v1/manifests", headers=other_customer_headers).json()
    assert listing == []

    # Ops sees everything.
    resp = client.get(f"/api/v1/manifests/{manifest['id']}", headers=ops_headers)
    assert resp.status_code == 200


def test_customer_cannot_manage_catalog_or_advance_states(client, customer_headers, ops_headers):
    resp = client.post(
        "/api/v1/launches", json={**WINDOW, "launch_date": iso_in(120)}, headers=customer_headers
    )
    assert resp.status_code == 403

    manifest = create_manifest(client, customer_headers)
    resp = client.post(
        f"/api/v1/manifests/{manifest['id']}/status",
        json={"to_state": "integrated"},
        headers=customer_headers,
    )
    assert resp.status_code == 403


def test_draft_only_editing(client, customer_headers, ops_headers):
    window = create_window(client, ops_headers)
    manifest = create_manifest(client, customer_headers)
    mid = manifest["id"]

    ok = client.patch(f"/api/v1/manifests/{mid}", json={"mass_kg": 120}, headers=customer_headers)
    assert ok.status_code == 200 and ok.json()["mass_kg"] == 120

    client.post(
        f"/api/v1/manifests/{mid}/quotes",
        json={"launch_window_id": window["id"]},
        headers=customer_headers,
    )
    frozen = client.patch(f"/api/v1/manifests/{mid}", json={"mass_kg": 130}, headers=customer_headers)
    assert frozen.status_code == 409


def test_tracking_with_unknown_token_is_404(client):
    assert client.get("/api/v1/tracking/not-a-real-token").status_code == 404
