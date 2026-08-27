import json
import hashlib
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from conftest import client, auth_header, random_phone, register_user


def future_date(days=14):
    return (datetime.utcnow() + timedelta(days=days)).replace(microsecond=0).isoformat()


def create_cheque(drawer, payee_phone, amount=500000, memo="Test memo", due=None):
    body = {
        "payee_phone": payee_phone,
        "amount_paise": amount,
        "due_date": due or future_date(),
        "memo": memo,
    }
    res = client.post("/cheques", json=body, headers=auth_header(drawer))
    return res


def compute_hash(cheque_json, memo_override=None):
    """Mirrors app/crypto_utils.py's compute_cheque_hash exactly."""
    payload = {
        "amount_paise": cheque_json["amount_paise"],
        "cheque_id": cheque_json["id"],
        "drawer_id": cheque_json["drawer_id"],
        "due_date": cheque_json["due_date"],
        "memo": cheque_json["memo"] or "",
        "payee_phone": cheque_json["payee_phone"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).digest()


# ---------- Create ----------

def test_create_cheque_to_registered_payee(drawer, payee):
    res = create_cheque(drawer, payee["phone"])
    assert res.status_code == 200
    body = res.json()
    assert body["current_state"] == "draft"
    assert body["payee_id"] == payee["user_id"]


def test_create_cheque_to_unregistered_payee(drawer):
    res = create_cheque(drawer, random_phone())
    assert res.status_code == 200
    body = res.json()
    assert body["current_state"] == "pending_registration"
    assert body["payee_id"] is None


def test_create_cheque_negative_amount_rejected(drawer, payee):
    res = create_cheque(drawer, payee["phone"], amount=-100)
    assert res.status_code == 422


def test_create_cheque_malformed_due_date_rejected(drawer, payee):
    body = {
        "payee_phone": payee["phone"],
        "amount_paise": 500000,
        "due_date": "not-a-date",
    }
    res = client.post("/cheques", json=body, headers=auth_header(drawer))
    assert res.status_code == 422


# ---------- Sign ----------

def test_sign_cheque_with_valid_signature(signed_up_drawer_with_key, payee):
    drawer = signed_up_drawer_with_key
    created = create_cheque(drawer, payee["phone"]).json()

    digest = compute_hash(created)
    signature = drawer["private_key"].sign(digest, ec.ECDSA(hashes.SHA256()))

    res = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": signature.hex()},
        headers=auth_header(drawer),
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "created"


def test_sign_with_garbage_signature_rejected(signed_up_drawer_with_key, payee):
    drawer = signed_up_drawer_with_key
    created = create_cheque(drawer, payee["phone"]).json()

    res = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": "00112233"},
        headers=auth_header(drawer),
    )
    assert res.status_code == 400


def test_sign_as_wrong_user_forbidden(signed_up_drawer_with_key, payee):
    drawer = signed_up_drawer_with_key
    created = create_cheque(drawer, payee["phone"]).json()

    res = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": "00112233"},
        headers=auth_header(payee),  # payee, not drawer
    )
    assert res.status_code == 403


def test_sign_without_public_key_rejected(drawer, payee):
    # 'drawer' fixture here has NOT uploaded a public key
    created = create_cheque(drawer, payee["phone"]).json()
    res = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": "00112233"},
        headers=auth_header(drawer),
    )
    assert res.status_code == 400


def test_sign_already_signed_cheque_rejected(signed_up_drawer_with_key, payee):
    drawer = signed_up_drawer_with_key
    created = create_cheque(drawer, payee["phone"]).json()
    digest = compute_hash(created)
    signature = drawer["private_key"].sign(digest, ec.ECDSA(hashes.SHA256()))

    first = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": signature.hex()},
        headers=auth_header(drawer),
    )
    assert first.status_code == 200

    second = client.post(
        f"/cheques/{created['id']}/sign",
        json={"signature_hex": signature.hex()},
        headers=auth_header(drawer),
    )
    assert second.status_code == 400


# ---------- List ----------

def test_issued_list_scoped_to_drawer(drawer, payee):
    create_cheque(drawer, payee["phone"])
    res = client.get("/cheques?role=issued", headers=auth_header(drawer))
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_received_list_shows_linked_cheque(drawer, payee):
    create_cheque(drawer, payee["phone"])
    res = client.get("/cheques?role=received", headers=auth_header(payee))
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_invalid_role_rejected(drawer):
    res = client.get("/cheques?role=bogus", headers=auth_header(drawer))
    assert res.status_code == 422


def test_empty_received_list_for_fresh_user(payee):
    res = client.get("/cheques?role=received", headers=auth_header(payee))
    assert res.status_code == 200
    assert res.json() == []


# ---------- Cancel ----------

def test_cancel_draft_cheque(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()
    res = client.post(
        f"/cheques/{created['id']}/cancel",
        json={"reason": "test cancel"},
        headers=auth_header(drawer),
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "cancelled"


def test_cannot_cancel_twice(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()
    client.post(f"/cheques/{created['id']}/cancel", json={}, headers=auth_header(drawer))
    second = client.post(f"/cheques/{created['id']}/cancel", json={}, headers=auth_header(drawer))
    assert second.status_code == 400


def test_payee_cannot_cancel(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()
    res = client.post(f"/cheques/{created['id']}/cancel", json={}, headers=auth_header(payee))
    assert res.status_code == 403


def test_cancel_pending_registration_cheque(drawer):
    created = create_cheque(drawer, random_phone()).json()
    assert created["current_state"] == "pending_registration"
    res = client.post(f"/cheques/{created['id']}/cancel", json={}, headers=auth_header(drawer))
    assert res.status_code == 200  # regression check for the M3 Day 6 fix


# ---------- Detail ----------

def test_detail_visible_to_drawer_and_payee(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()

    as_drawer = client.get(f"/cheques/{created['id']}", headers=auth_header(drawer))
    assert as_drawer.status_code == 200

    as_payee = client.get(f"/cheques/{created['id']}", headers=auth_header(payee))
    assert as_payee.status_code == 200


def test_detail_hidden_from_unrelated_user(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()
    unrelated = register_user(random_phone())
    res = client.get(f"/cheques/{created['id']}", headers=auth_header(unrelated))
    assert res.status_code == 403


def test_detail_includes_full_transition_history(drawer, payee):
    created = create_cheque(drawer, payee["phone"]).json()
    client.post(f"/cheques/{created['id']}/cancel", json={"reason": "history check"}, headers=auth_header(drawer))

    res = client.get(f"/cheques/{created['id']}", headers=auth_header(drawer))
    transitions = res.json()["transitions"]
    assert len(transitions) == 2  # created, then cancelled
    assert transitions[-1]["to_state"] == "cancelled"
    assert transitions[-1]["reason"] == "history check"