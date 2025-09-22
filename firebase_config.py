import firebase_admin
from firebase_admin import credentials, db as rtdb
import os


# Expect a service account JSON at ./serviceAccountKey.json
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "https://cse3311-4edfb-default-rtdb.firebaseio.com")
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")


if not firebase_admin._apps:
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred, {
'databaseURL': FIREBASE_DB_URL
})


# Expose db reference factory
class _DB:
def reference(self, path: str = "/"):
return rtdb.reference(path)


db = _DB()