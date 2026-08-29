def test_catalogue_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Notebook" in response.data


def test_search_returns_matching_product(client):
    response = client.get("/search?q=Mouse")
    assert response.status_code == 200
    assert b"Wireless Mouse" in response.data


def test_shopper_can_log_in(client, login_as):
    response = login_as()
    assert b"shopper (shopper)" in response.data


def test_logged_out_user_is_redirected_from_cart(client):
    response = client.get("/cart")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_shopper_is_blocked_from_admin(client, login_as):
    login_as()
    response = client.get("/admin")
    assert response.status_code == 403
    assert b"Administrator access is required" in response.data
