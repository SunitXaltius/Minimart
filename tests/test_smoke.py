"""Small starting-gate smoke tests for MiniMart."""


def login_as_shopper(client):
    """Log in using the shopper account created by init_db()."""
    return client.post(
        "/login",
        data={"username": "shopper", "password": "password1"},
    )


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Notebook" in response.data


def test_search_finds_a_product(client):
    response = client.get("/search?q=Notebook")

    assert response.status_code == 200
    assert b"Notebook" in response.data


def test_logged_out_user_is_redirected_from_cart(client):
    response = client.get("/cart")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_shopper_can_log_in_and_view_cart(client):
    login_response = login_as_shopper(client)

    assert login_response.status_code == 302

    cart_response = client.get("/cart")
    assert cart_response.status_code == 200


def test_shopper_cannot_open_admin_page(client):
    login_as_shopper(client)

    response = client.get("/admin")

    assert response.status_code == 403
    assert b"Administrator access is required" in response.data
