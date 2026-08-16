def test_cannot_cancel_already_cancelled(client, auth_headers, signed_cheque):
    # first cancel — should succeed
    res1 = client.post(f"/cheques/{signed_cheque.id}/cancel", json={}, headers=auth_headers)
    assert res1.status_code == 200

    # second cancel — should fail
    res2 = client.post(f"/cheques/{signed_cheque.id}/cancel", json={}, headers=auth_headers)
    assert res2.status_code == 400

def test_payee_cannot_cancel(client, payee_auth_headers, signed_cheque):
    res = client.post(f"/cheques/{signed_cheque.id}/cancel", json={}, headers=payee_auth_headers)
    assert res.status_code == 403

def test_multiple_pending_cheques_all_resolve(client, test_user):
    phone = "+919666666666"
    db = SessionLocal()
    for i in range(3):
        db.add(Cheque(
            drawer_id=test_user.id, payee_id=None, payee_phone=phone,
            amount_paise=5000 * (i + 1),
            due_date=datetime.utcnow() + timedelta(days=5),
            current_state=ChequeState.pending_registration,
        ))
    db.commit()
    db.close()

    req = client.post("/auth/otp/request", json={"phone_number": phone})
    session_token = req.json()["session_token"]
    client.post("/auth/otp/verify", json={"session_token": session_token, "code": "123456"})

    db = SessionLocal()
    resolved = db.query(Cheque).filter(Cheque.payee_phone == phone).all()
    assert all(c.current_state == ChequeState.draft for c in resolved)
    assert all(c.payee_id is not None for c in resolved)
    db.close()