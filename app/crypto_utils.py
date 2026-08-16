import hashlib
import json
from app.models.models import Cheque


def compute_cheque_hash(cheque: Cheque) -> bytes:
    payload = {
        "amount_paise": cheque.amount_paise,
        "cheque_id": str(cheque.id),
        "drawer_id": str(cheque.drawer_id),
        "due_date": cheque.due_date.isoformat(),
        "memo": cheque.memo or "",
        "payee_phone": cheque.payee_phone,
    }
    # Fixed typo: separators (with an 'a')
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).digest()