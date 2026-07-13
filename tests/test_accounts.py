"""Real customer accounts: registration, email verification, login with
progressive lockout, and password reset — end to end through the API."""

import pytest

import app.modules.accounts.service as account_service


@pytest.fixture
def mailbox(monkeypatch):
    """Capture transactional emails and expose the single-use token in each."""
    sent = []

    def fake_send(to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(account_service, "send_email", fake_send)
    return sent


def _token_from(email_body: str) -> str:
    # Links end with /<token>; the token is the last path segment.
    return email_body.strip().split("/")[-1].split()[0]


def register(client, mailbox, email="maria@agrosat.gt", password="orbita-pass-1"):
    resp = client.post(
        "/api/v1/accounts/register",
        json={"email": email, "display_name": "María F.", "password": password},
    )
    assert resp.status_code == 201, resp.text
    # The service lowercases the address, so match case-insensitively.
    verify_link = [m for m in mailbox if m["to"] == email.strip().lower()][-1]["body"]
    return resp.json(), _token_from(verify_link)


def test_register_sends_verification_and_blocks_login_until_verified(client, mailbox):
    user, token = register(client, mailbox)
    assert user["email_verified"] is False
    assert user["email"] == "maria@agrosat.gt"

    early = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    )
    assert early.status_code == 403
    assert "verif" in early.json()["detail"].lower()

    verified = client.post("/api/v1/accounts/verify", json={"token": token})
    assert verified.status_code == 200

    ok = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]


def test_logged_in_account_can_use_the_platform(client, mailbox):
    _, token = register(client, mailbox)
    client.post("/api/v1/accounts/verify", json={"token": token})
    jwt = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    ).json()["access_token"]

    headers = {"Authorization": f"Bearer {jwt}"}
    created = client.post("/api/v1/manifests", json={"name": "AgroSat-1"}, headers=headers)
    assert created.status_code == 201
    # The manifest is owned by the account and listed for it.
    listing = client.get("/api/v1/manifests", headers=headers).json()
    assert [m["name"] for m in listing] == ["AgroSat-1"]


def test_duplicate_email_is_rejected(client, mailbox):
    register(client, mailbox)
    dup = client.post(
        "/api/v1/accounts/register",
        json={"email": "maria@agrosat.gt", "display_name": "Otra", "password": "x" * 8},
    )
    assert dup.status_code == 409


def test_email_is_normalized_and_validated(client, mailbox):
    user, _ = register(client, mailbox, email="MixedCase@Example.COM")
    assert user["email"] == "mixedcase@example.com"

    bad = client.post(
        "/api/v1/accounts/register",
        json={"email": "not-an-email", "display_name": "X", "password": "x" * 8},
    )
    assert bad.status_code == 422


def test_wrong_password_locks_after_threshold(client, mailbox):
    _, token = register(client, mailbox)
    client.post("/api/v1/accounts/verify", json={"token": token})

    # Threshold is 3 (conftest). First 3 wrong tries return 401...
    for _ in range(3):
        r = client.post(
            "/api/v1/accounts/login",
            json={"email": "maria@agrosat.gt", "password": "wrong"},
        )
        assert r.status_code == 401

    # ...the account is now locked: even the correct password is refused.
    locked = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    )
    assert locked.status_code == 429


def test_login_does_not_reveal_unknown_email(client, mailbox):
    unknown = client.post(
        "/api/v1/accounts/login",
        json={"email": "nobody@nowhere.com", "password": "whatever"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Email or password is incorrect."


def test_password_reset_flow(client, mailbox):
    _, token = register(client, mailbox)
    client.post("/api/v1/accounts/verify", json={"token": token})

    # request-reset is always generic (no account enumeration)...
    generic = client.post(
        "/api/v1/accounts/request-reset", json={"email": "nobody@nowhere.com"}
    )
    assert generic.status_code == 200

    client.post("/api/v1/accounts/request-reset", json={"email": "maria@agrosat.gt"})
    reset_body = [m for m in mailbox if "contraseña" in m["subject"].lower()][-1]["body"]
    reset_token = _token_from(reset_body)

    done = client.post(
        "/api/v1/accounts/reset",
        json={"token": reset_token, "password": "brand-new-pass"},
    )
    assert done.status_code == 200

    # Old password no longer works; new one does.
    old = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "brand-new-pass"},
    )
    assert new.status_code == 200


def test_verify_with_bad_token_fails(client, mailbox):
    register(client, mailbox)
    resp = client.post("/api/v1/accounts/verify", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_account_events_are_audited(client, mailbox, db):
    from app.modules.manifests.models import ManifestEvent

    _, token = register(client, mailbox)
    client.post("/api/v1/accounts/verify", json={"token": token})
    client.post(
        "/api/v1/accounts/login",
        json={"email": "maria@agrosat.gt", "password": "orbita-pass-1"},
    )

    types = {e.event_type for e in db.query(ManifestEvent).all()}
    assert {"account.registered", "account.verified", "account.login"} <= types
