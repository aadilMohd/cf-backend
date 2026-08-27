import pytest
import uuid
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

from app.main import app

client = TestClient(app)


def random_phone():
    """Generates a unique fake Indian-format phone number per test."""
    return "+91" + str(uuid.uuid4().int)[:10]


def register_user(phone: str):
    """Runs a phone number through the real OTP request/verify flow.
    Relies on the hardcoded dev OTP code '123456' — update here if
    USE_REAL_OTP is ever flipped on for this test environment."""
    req = client.post("/auth/otp/request", json={"phone_number": phone})
    assert req.status_code == 200
    session_token = req.json()["session_token"]

    verify = client.post("/auth/otp/verify", json={
        "session_token": session_token,
        "code": "123456",
    })
    assert verify.status_code == 200
    data = verify.json()
    return {
        "phone": phone,
        "access_token": data["access_token"],
        "user_id": data["user_id"],
        "is_new_user": data["is_new_user"],
    }


def auth_header(user):
    return {"Authorization": f"Bearer {user['access_token']}"}


@pytest.fixture
def drawer():
    """A fresh registered user acting as the cheque drawer."""
    return register_user(random_phone())


@pytest.fixture
def payee():
    """A fresh registered user acting as the cheque payee."""
    return register_user(random_phone())


@pytest.fixture
def keypair():
    """A real ECDSA P-256 keypair for signing tests."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {"private_key": private_key, "public_key_pem": pem}


@pytest.fixture
def signed_up_drawer_with_key(drawer, keypair):
    """A drawer with a public key already uploaded — the common
    precondition for every signing test."""
    res = client.put(
        "/users/me/public-key",
        json={"public_key_pem": keypair["public_key_pem"]},
        headers=auth_header(drawer),
    )
    assert res.status_code == 200
    return {**drawer, **keypair}