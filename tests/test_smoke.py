"""Small starting-gate smoke tests for MiniMart."""


def login_as_shopper(client):
    """Log in through MiniMart's real shopper account."""
    return client.post(
        "/login",
        data={"username": "shopper", "password": "password1"},
    )


# If this fails, customers cannot see the MiniMart product catalogue.
def test_catalogue_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Notebook" in response.data


# If this fails, customers cannot find a matching product through search.
def test_search_returns_matching_product(client):
    response = client.get("/search?q=Mouse")
    assert response.status_code == 200
    assert b"Wireless Mouse" in response.data


# If this fails, a shopper cannot authenticate with valid credentials.
def test_shopper_can_log_in(client):
    response = login_as_shopper(client)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    with client.session_transaction() as session_data:
        assert session_data["username"] == "shopper"
        assert session_data["role"] == "shopper"


# If this fails, a logged-out visitor could open the protected cart page.
def test_logged_out_user_is_redirected_from_cart(client):
    response = client.get("/cart")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# If this fails, an ordinary shopper could access administrator pages.
def test_shopper_is_blocked_from_admin(client):
    login_as_shopper(client)

    response = client.get("/admin")

    assert response.status_code == 403
    assert b"Administrator access is required" in response.data
