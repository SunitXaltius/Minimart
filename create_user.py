import getpass
import sqlite3

from werkzeug.security import generate_password_hash

from app import create_app, init_db


def create_user():
    app = create_app()
    with app.app_context():
        init_db()

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    role = input("Role (admin/shopper): ").strip().lower()

    if not username:
        print("Username cannot be empty.")
        return

    if not password:
        print("Password cannot be empty.")
        return

    if password != confirm_password:
        print("The passwords do not match.")
        return

    if role not in ("admin", "shopper"):
        print("Role must be admin or shopper.")
        return

    password_hash = generate_password_hash(password)
    connection = sqlite3.connect(app.config["DATABASE"])

    try:
        connection.execute(
            "INSERT INTO users (username, password_hash, role) "
            "VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        connection.commit()
        print(f"User '{username}' created successfully.")
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists.")
    finally:
        connection.close()


if __name__ == "__main__":
    create_user()
