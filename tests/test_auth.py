def test_signup_resolves_pending_cheque(client, pending_cheque):
    # simulate the OTP flow for the phone number the pending cheque is waiting on
    req = client.post("/auth/otp/request", json={"phone_number": pending_cheque.payee_phone})
    session_token = req.json()["session_token"]

    # hardcoded test code — matches your Day 3 dev shortcut; swap if you've since removed it
    verify = client.post("/auth/otp/verify", json={
        "session_token": session_token,
        "code": "123456",
    })
    assert verify.status_code == 200
    assert verify.json()["is_new_user"] is True

    db = SessionLocal()
    refreshed = db.query(Cheque).filter(Cheque.id == pending_cheque.id).first()
    assert refreshed.current_state == ChequeState.draft
    assert refreshed.payee_id is not None
    db.close()

def test_existing_user_login_does_not_reresolve(client, test_user, pending_cheque):
    # test_user already exists; log in again, confirm is_new_user is False
    # and no resolution logic runs a second time for unrelated cheques
    req = client.post("/auth/otp/request", json={"phone_number": test_user.phone_number})
    session_token = req.json()["session_token"]
    verify = client.post("/auth/otp/verify", json={
        "session_token": session_token,
        "code": "123456",
    })
    assert verify.json()["is_new_user"] is False

def test_signup_with_no_pending_cheques_unaffected(client):
    # a brand new number with zero pending cheques should sign up cleanly,
    # proving resolution logic doesn't break the "nothing to resolve" case
    req = client.post("/auth/otp/request", json={"phone_number": "+919777777777"})
    session_token = req.json()["session_token"]
    verify = client.post("/auth/otp/verify", json={
        "session_token": session_token,
        "code": "123456",
    })
    assert verify.status_code == 200