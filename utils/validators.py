import re


def valid_email(email: str) -> bool:
pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
return re.match(pattern, email) is not None


# Normalize an email to a safe key (no dots) for Realtime DB keys


def normalize_email_key(email: str) -> str:
return re.sub(r"[^a-z0-9]", "_", email.lower())