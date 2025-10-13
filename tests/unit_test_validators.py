import os
import sys
# Make sure project root is on sys.path so `import app` works:
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    
from utils.validators import valid_email, normalize_email, normalize_email_key, validate_name, validate_role

def test_valid_email():
    assert valid_email("student@university.edu")
    assert not valid_email("bad-email")
    assert valid_email(" A.B@Example.COM ")

def test_normalize_email():
    assert normalize_email("TEST@EX.COM ") == "test@ex.com"

def test_normalize_email_key():
    assert normalize_email_key("Test.Email@uta.edu ") == "test_email_uta_edu"

def test_validate_name_and_role():
    assert validate_name("Alice Johnson")
    assert not validate_name("")
    assert validate_role("Member")
    assert not validate_role("invalid-role")