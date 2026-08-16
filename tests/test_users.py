def test_search_requires_auth(client):
    response = client.get("/users/search?phone=+919999999999")
    assert response.status_code in (401, 403)

def test_search_returns_user(client, auth_headers, test_user):
    response = client.get(f"/users/search?phone={test_user.phone_number}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)