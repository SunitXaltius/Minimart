"""Edge-case tests for MiniMart's important failure paths."""

import pytest

from app import get_db


def _login(client, username, password):
    """Log in through MiniMart's real login route."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
    )


def _count_rows(app, query, parameters=()):
    """Return a row count from the temporary test database."""
    with app.app_context():
        connection = get_db()
        count = connection.execute(query, parameters).fetchone()[0]
        connection.close()
    return count


# If this fails, an empty checkout could create a false order or show success.
def test_checkout_rejects_empty_cart_without_creating_order(client, app):
    _login(client, "shopper", "password1")

    response = client.post("/checkout")

    assert response.status_code == 302
    assert response.headers["Location"] == "/cart"
    cart_response = client.get("/cart")
    assert b"Your cart is empty" in cart_response.data
    assert _count_rows(app, "SELECT COUNT(*) FROM orders") == 0


# If this fails, an administrator could save a product with an impossible negative price.
def test_admin_add_rejects_negative_price_without_creating_product(client, app):
    _login(client, "admin", "admin123")

    response = client.post(
        "/admin/add",
        data={"name": "Negative Product", "description": "Invalid", "price": "-1"},
    )

    assert response.status_code == 400
    assert b"Price cannot be negative" in response.data
    assert _count_rows(
        app,
        "SELECT COUNT(*) FROM products WHERE name = ?",
        ("Negative Product",),
    ) == 0


# If this fails, invalid price text could crash the page or enter bad product data.
def test_admin_add_rejects_non_numeric_price_without_creating_product(client, app):
    _login(client, "admin", "admin123")

    response = client.post(
        "/admin/add",
        data={"name": "Text Price Product", "description": "Invalid", "price": "abc"},
    )

    assert response.status_code == 400
    assert b"Price must be a number" in response.data
    assert _count_rows(
        app,
        "SELECT COUNT(*) FROM products WHERE name = ?",
        ("Text Price Product",),
    ) == 0


# If this fails, registration could create two accounts with the same username.
def test_registration_rejects_existing_username_without_creating_duplicate(client, app):
    count_before = _count_rows(
        app,
        "SELECT COUNT(*) FROM users WHERE username = ?",
        ("shopper",),
    )

    response = client.post(
        "/register",
        data={"username": "shopper", "password": "different-password"},
    )

    count_after = _count_rows(
        app,
        "SELECT COUNT(*) FROM users WHERE username = ?",
        ("shopper",),
    )
    assert response.status_code == 409
    assert b"That username is already registered" in response.data
    assert count_before == 1
    assert count_after == count_before


# If this fails, a shopper could view an admin page or submit an admin action directly.
@pytest.mark.parametrize(
    ("method", "path", "data"),
    [
        ("GET", "/admin", None),
        ("GET", "/admin/add", None),
        (
            "POST",
            "/admin/add",
            {"name": "Blocked Product", "description": "Forbidden", "price": "10"},
        ),
    ],
    ids=["admin-page", "add-product-page", "add-product-post"],
)
def test_shopper_is_forbidden_from_every_admin_route(client, app, method, path, data):
    _login(client, "shopper", "password1")

    response = client.open(path, method=method, data=data)

    assert response.status_code == 403
    assert b"Administrator access is required" in response.data
    assert _count_rows(
        app,
        "SELECT COUNT(*) FROM products WHERE name = ?",
        ("Blocked Product",),
    ) == 0


# If this fails, knowing a username would be enough to enter another user's account.
def test_login_rejects_correct_username_with_wrong_password(client):
    response = client.post(
        "/login",
        data={"username": "shopper", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as session_data:
        assert "username" not in session_data
        assert "role" not in session_data
