"""Pytest fixtures. API tests run against an isolated SQLite database so they
need no external DB setup; the same models power both engines."""
import os
import pathlib
import tempfile

# Point the app at a throwaway SQLite DB BEFORE importing any app module.
_db_file = pathlib.Path(tempfile.gettempdir()) / "ckin_pytest.db"
if _db_file.exists():
    _db_file.unlink()
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_file.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_secret  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # The login limiter keeps in-process state; clear it between tests.
    from app import security

    security._attempts.clear()
    yield
    security._attempts.clear()


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    return TestClient(app)


@pytest.fixture()
def user(db):
    u = User(
        full_name="Hpatel",
        email="hpatel@ckinckout.example",
        password_hash=hash_secret("admin1234"),
        hourly_rate=10.00,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def auth_header(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
