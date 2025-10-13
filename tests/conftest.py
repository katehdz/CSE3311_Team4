# tests/conftest.py
import os
import sys
from types import SimpleNamespace
import pytest

# Ensure project root is on sys.path so `import app` resolves
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Now import the Flask app module
import app as appmod  # noqa: E402

@pytest.fixture
def client(monkeypatch):
    """
    Flask test client fixture that replaces app.db with a lightweight fake DB.
    This avoids hitting real Firestore during tests.
    """
    # Create a minimal fake DB with the attributes your tests and app expect.
    fake_db = SimpleNamespace(
        # students
        get_student=lambda sid: None,
        get_student_by_email=lambda e: None,
        get_all_students=lambda: [],
        create_student=lambda data: "STUDENT_FAKE_ID",
        update_student=lambda sid, data: True,
        delete_student=lambda sid: True,
        # clubs
        get_all_clubs=lambda: [],
        get_club=lambda cid: None,
        create_club=lambda data: "CLUB_FAKE_ID",
        update_club=lambda cid, data: True,
        delete_club=lambda cid: True,
        # memberships
        get_club_members=lambda cid: [],
        add_member_to_club=lambda cid, sid, role: "MEM_FAKE_ID",
        remove_member_from_club=lambda cid, sid: True,
        update_member_role=lambda cid, sid, r: True,
        # utilities
        update_club_member_count=lambda cid: 0,
    )

    # Patch the app's db with the fake DB before tests run
    monkeypatch.setattr(appmod, "db", fake_db)

    # Provide Flask test client
    appmod.app.config["TESTING"] = True
    with appmod.app.test_client() as client:
        yield client