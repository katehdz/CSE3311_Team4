import re
from logger import get_logger

logger = get_logger(__name__)
logger.debug("validators module loaded")

ALLOWED_ROLES = {"Member", "Officer", "President", "Vice President", "Treasurer", "Secretary"}

def valid_email(email: str) -> bool:
    """
    Validate an email address using a stricter pattern.
    - Username part allows alphanumeric, underscore, period, hyphen, plus sign
    - Domain part enforces proper domain formatting
    - TLD part ensures at least 2 characters
    - Prevents double periods in username and domain
    """
    if not email:
        return False
        
    # Trim whitespace first
    email = email.strip()
    
    # Check for common formatting issues
    if '..' in email or email.startswith('.') or email.endswith('.'):
        return False
        
    # Main pattern check - more comprehensive than before
    pattern = r"^[A-Za-z0-9][\w.%+-]*@([A-Za-z0-9][\w-]*\.)+[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None

def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()

def normalize_email_key(email: str) -> str:
    if not email:
        return ""
    return email.strip().replace("@", "_").replace(".", "_").lower()

def validate_name(name: str, min_len: int = 2, max_len: int = 80) -> bool:
    if not name:
        return False
    s = name.strip()
    if len(s) < min_len or len(s) > max_len:
        return False
    if re.search(r'[\x00-\x1f\x7f]', s):
        return False
    return True

def validate_role(role: str) -> bool:
    return bool(role and role in ALLOWED_ROLES)

def sanitize_input(text: str, max_len: int = 500) -> str:
    if text is None:
        return ""
    s = re.sub(r'[\x00-\x1f\x7f]', '', str(text))
    s = s.strip()
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s