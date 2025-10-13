import os
import sys
# Make sure project root is on sys.path so `import app` works:
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from types import SimpleNamespace
import app as appmod

def test_delete_student_not_found(client, monkeypatch):
    # Ensure db.get_student returns None -> 404
    monkeypatch.setattr(appmod, "db", SimpleNamespace(get_student=lambda sid: None))
    rv = client.delete("/api/students/doesnotexist")
    assert rv.status_code == 404
    assert rv.get_json()["success"] is False

def test_delete_student_success(client, monkeypatch):
    called = {}
    def fake_get_student(sid):
        return {"id": sid, "email": "a@b.com"}
    def fake_delete_student(sid):
        called["deleted"] = sid
        return True
    monkeypatch.setattr(appmod, "db", SimpleNamespace(get_student=fake_get_student, delete_student=fake_delete_student))
    rv = client.delete("/api/students/abc123")
    assert rv.status_code == 200
    assert rv.get_json()["success"] is True
    assert called.get("deleted") == "abc123"