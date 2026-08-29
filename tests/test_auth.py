"""Authentication and registration tests for MiniMart."""

from werkzeug.security import check_password_hash

from app import get_db


def _find_user(app, username):
    """Return one user row from the temporary test database."""
    with app.app_context():
        connection = get_db()
        user = connection.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        connection.close()
    return user


# If this fails, a new shopper cannot create an account and continue to login.
def test_registration_creates_new_shopper_account(client, app):
    response = client.post(
        "/register",
        data={"username": "newshopper", "password": "safe-password"},
    )

    user = _find_user(app, "newshopper")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert user is not None
    assert user["role"] == "shopper"


# If this fails, MiniMart may save a new user's real password in the database.
def test_registration_hashes_password(client, app):
    password = "safe-password"
    client.post(
        "/register",
        data={"username": "hasheduser", "password": password},
    )

    user = _find_user(app, "hasheduser")
    assert user is not None
    assert user["password_hash"] != password
    assert check_password_hash(user["password_hash"], password)


# If this fails, someone could create their own administrator account through registration.
def test_registration_ignores_submitted_admin_role(client, app):
    client.post(
        "/register",
        data={
            "username": "roleattacker",
            "password": "safe-password",
            "role": "admin",
        },
    )

    user = _find_user(app, "roleattacker")
    assert user is not None
    assert user["role"] == "shopper"


# If this fails, MiniMart could create an account without a username.
def test_registration_rejects_missing_username(client):
    response = client.post(
        "/register",
        data={"username": "", "password": "safe-password"},
    )

    assert response.status_code == 400
    assert b"Username and password are required" in response.data


# If this fails, MiniMart could create an account without a password.
def test_registration_rejects_missing_password(client):
    response = client.post(
        "/register",
        data={"username": "nopassword", "password": ""},
    )

    assert response.status_code == 400
    assert b"Username and password are required" in response.data


# If this fails, two users could be created with the same username.
def test_registration_rejects_duplicate_username(client):
    response = client.post(
        "/register",
        data={"username": "shopper", "password": "another-password"},
    )

    assert response.status_code == 409
    assert b"That username is already registered" in response.data


# If this fails, valid credentials would not create the correct logged-in session.
def test_login_stores_username_and_role_in_session(client):
    response = client.post(
        "/login",
        data={"username": "shopper", "password": "password1"},
    )

    with client.session_transaction() as session_data:
        assert response.status_code == 302
        assert response.headers["Location"] == "/"
        assert session_data["username"] == "shopper"
        assert session_data["role"] == "shopper"


# If this fails, a shopper could log in by supplying an incorrect password.
def test_login_rejects_wrong_password(client):
    response = client.post(
        "/login",
        data={"username": "shopper", "password": "wrong-password"},
    )

    with client.session_transaction() as session_data:
        assert "username" not in session_data
    assert b"Invalid username or password" in response.data


# If this fails, MiniMart could create a session for a username that does not exist.
def test_login_rejects_unknown_username(client):
    response = client.post(
        "/login",
        data={"username": "missing-user", "password": "some-password"},
    )

    with client.session_transaction() as session_data:
        assert "username" not in session_data
    assert b"Invalid username or password" in response.data


# If this fails, using Logout would leave the shopper authenticated.
def test_logout_clears_authenticated_session(client):
    client.post(
        "/login",
        data={"username": "shopper", "password": "password1"},
    )

    response = client.get("/logout")

    with client.session_transaction() as session_data:
        assert "username" not in session_data
        assert "role" not in session_data
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
