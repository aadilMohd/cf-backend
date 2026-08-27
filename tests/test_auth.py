from conftest import client, random_phone, register_user


def test_otp_request_returns_session_token():
    res = client.post("/auth/otp/request", json={"phone_number": random_phone()})
    assert res.status_code == 200
    assert "session_token" in res.json()


def test_otp_verify_wrong_code_rejected():
    phone = random_phone()
    req = client.post("/auth/otp/request", json={"phone_number": phone})
    session_token = req.json()["session_token"]

    res = client.post("/auth/otp/verify", json={
        "session_token": session_token,
        "code": "000000",
    })
    assert res.status_code == 400


def test_otp_verify_creates_new_user():
    user = register_user(random_phone())
    assert user["is_new_user"] is True
    assert "access_token" in user


def test_otp_session_token_single_use():
    phone = random_phone()
    req = client.post("/auth/otp/request", json={"phone_number": phone})
    session_token = req.json()["session_token"]

    first = client.post("/auth/otp/verify", json={"session_token": session_token, "code": "123456"})
    assert first.status_code == 200

    second = client.post("/auth/otp/verify", json={"session_token": session_token, "code": "123456"})
    assert second.status_code == 400


def test_existing_user_login_is_not_new():
    phone = random_phone()
    first = register_user(phone)
    assert first["is_new_user"] is True

    # log in again with the same number
    req = client.post("/auth/otp/request", json={"phone_number": phone})
    session_token = req.json()["session_token"]
    second = client.post("/auth/otp/verify", json={"session_token": session_token, "code": "123456"})
    assert second.status_code == 200
    assert second.json()["is_new_user"] is False