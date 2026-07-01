"""End-to-end API tests over the SQLite test database."""
from tests.conftest import auth_header


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert meta["business_name"] == "CK_IN&CK_OUT"
    assert meta["manager_name"] == "Hpatel"


def test_login_bad_password(client, user):
    resp = client.post(
        "/api/auth/login",
        json={"email": "hpatel@ckinckout.example", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_rate_limit(client, user):
    # 5 allowed attempts, 6th is blocked.
    last = None
    for _ in range(6):
        last = client.post(
            "/api/auth/login",
            json={"email": "hpatel@ckinckout.example", "password": "wrong"},
        )
    assert last.status_code == 429


def test_clock_in_out_flow(client, user):
    hdr = auth_header(client, "hpatel@ckinckout.example", "admin1234")

    r1 = client.post("/api/clock-in", headers=hdr)
    assert r1.status_code == 201
    assert r1.json()["entry"]["status"] == "open"

    # Second clock-in is rejected (no double open shifts).
    r2 = client.post("/api/clock-in", headers=hdr)
    assert r2.status_code == 409

    r3 = client.post("/api/clock-out", headers=hdr)
    assert r3.status_code == 200
    assert r3.json()["entry"]["status"] == "closed"
    assert r3.json()["entry"]["total_minutes"] is not None

    # Clock-out with nothing open -> 409.
    r4 = client.post("/api/clock-out", headers=hdr)
    assert r4.status_code == 409


def test_clock_out_requires_auth(client):
    assert client.post("/api/clock-out").status_code == 401


def test_summary_and_history(client, user):
    hdr = auth_header(client, "hpatel@ckinckout.example", "admin1234")
    client.post("/api/clock-in", headers=hdr)
    client.post("/api/clock-out", headers=hdr)

    summary = client.get("/api/timesheet/me/summary", headers=hdr).json()
    assert "today" in summary and "week" in summary and "month" in summary
    assert summary["open_entry"] is None

    history = client.get("/api/timesheet/me", headers=hdr).json()
    assert len(history) == 1


def test_export_csv(client, user):
    hdr = auth_header(client, "hpatel@ckinckout.example", "admin1234")
    client.post("/api/clock-in", headers=hdr)
    client.post("/api/clock-out", headers=hdr)

    export = client.get("/api/timesheet/me/export?format=csv", headers=hdr)
    assert export.status_code == 200
    assert "Clock In (UTC)" in export.text


def test_correct_own_entry_writes_audit_log(client, user, db):
    from app.models import EntryAuditLog

    hdr = auth_header(client, "hpatel@ckinckout.example", "admin1234")
    client.post("/api/clock-in", headers=hdr)
    entry_id = client.post("/api/clock-out", headers=hdr).json()["entry"]["id"]

    resp = client.patch(
        f"/api/timesheet/me/entries/{entry_id}",
        headers=hdr,
        json={"notes": "Forgot to note the split shift", "reason": "manual fix"},
    )
    assert resp.status_code == 200
    assert resp.json()["edited_by"] is not None

    logs = db.query(EntryAuditLog).all()
    assert len(logs) >= 1
    assert any(log.field == "notes" for log in logs)


def test_bootstrap_creates_account_once(client, db):
    from app.main import _bootstrap_account
    from app.main import settings as main_settings
    from app.models import User
    from app.security import verify_secret

    main_settings.bootstrap_email = "hpatel@ckinckout.example"
    main_settings.bootstrap_password = "realpassword1"
    try:
        _bootstrap_account()
        users = db.query(User).all()
        assert len(users) == 1
        assert users[0].email == "hpatel@ckinckout.example"

        # Running again must not create a second account or reset the password.
        main_settings.bootstrap_password = "differentpassword"
        _bootstrap_account()
        assert db.query(User).count() == 1
        db.refresh(users[0])
        assert verify_secret("realpassword1", users[0].password_hash)
        assert not verify_secret("differentpassword", users[0].password_hash)
    finally:
        main_settings.bootstrap_email = None
        main_settings.bootstrap_password = None
        main_settings.force_password_reset = False


def test_bootstrap_force_password_reset(client, user, db):
    """A forgotten password can be recovered via FORCE_PASSWORD_RESET, without
    DB shell access, and it must not create a duplicate account."""
    from app.main import _bootstrap_account
    from app.main import settings as main_settings
    from app.security import verify_secret

    main_settings.bootstrap_email = user.email
    main_settings.bootstrap_password = "brand-new-password"
    main_settings.force_password_reset = True
    try:
        _bootstrap_account()
        assert db.query(type(user)).count() == 1
        db.refresh(user)
        assert verify_secret("brand-new-password", user.password_hash)

        hdr = auth_header(client, user.email, "brand-new-password")
        assert hdr["Authorization"].startswith("Bearer ")
    finally:
        main_settings.bootstrap_email = None
        main_settings.bootstrap_password = None
        main_settings.force_password_reset = False


def test_cannot_correct_someone_elses_entry(client, user, db):
    from app.models import User
    from app.security import hash_secret

    other = User(
        full_name="Other",
        email="other@ckinckout.example",
        password_hash=hash_secret("password123"),
        hourly_rate=10.00,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    hdr = auth_header(client, "hpatel@ckinckout.example", "admin1234")
    entry_id = client.post("/api/clock-in", headers=hdr).json()["entry"]["id"]

    other_hdr = auth_header(client, "other@ckinckout.example", "password123")
    resp = client.patch(
        f"/api/timesheet/me/entries/{entry_id}",
        headers=other_hdr,
        json={"notes": "should not work"},
    )
    assert resp.status_code == 404
