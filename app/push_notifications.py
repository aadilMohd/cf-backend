import logging
import os

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# Resolved relative to this file, not the working directory
_CRED_PATH = os.path.join(os.path.dirname(__file__), "secrets", "firebase-service-account.json")
_initialized = False


def _ensure_initialized() -> bool:
    global _initialized
    if _initialized:
        return True
    if not os.path.exists(_CRED_PATH):
        logger.warning("Firebase service account not found at %s; push disabled", _CRED_PATH)
        return False
    firebase_admin.initialize_app(credentials.Certificate(_CRED_PATH))
    _initialized = True
    return True


def send_push(fcm_token, title, body, data=None) -> bool:
    if not fcm_token or not _ensure_initialized():
        return False
    try:
        messaging.send(messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=fcm_token,
        ))
        return True
    except Exception:
        logger.exception("Push send failed")
        return False