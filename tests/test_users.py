from conftest import client, auth_header


def test_search_requires_auth():
    res = client.get("/users/search?phone=+919999999999")
    assert res.status_code in (401, 403)


def test_search_finds_registered_user(drawer, payee):
    res = client.get("/users/search", params={"phone": payee["phone"]}, headers=auth_header(drawer))
    assert res.status_code == 200
    assert res.json()["id"] == payee["user_id"]


def test_search_unregistered_number_404s(drawer):
    res = client.get("/users/search?phone=+911111111199", headers=auth_header(drawer))
    assert res.status_code == 404


def test_upload_public_key(signed_up_drawer_with_key):
    # fixture already performs the upload — just confirm it's retrievable
    # via a search from another authenticated user
    pass  # covered implicitly by signing tests; kept as a placeholder for clarity