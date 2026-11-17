"""Test setup: a throw-away database and mock AI, so tests never touch real data or APIs."""
import os
import tempfile

# These must be set BEFORE the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AI_MODE"] = "mock"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["APP_ENV"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:  # "with" runs startup (creates the tables)
        yield c


@pytest.fixture()
def make_client():
    """Creates extra independent browsers (each has its own cookies)."""
    clients = []

    def _make():
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
