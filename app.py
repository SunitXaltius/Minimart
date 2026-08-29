"""MiniMart after Lab 2 hardening.

Passwords are hashed, routes enforce roles, and secrets are loaded from the
environment. Rate limiting and CSRF protection remain documented limitations.
"""

import logging
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import load_config


def configure_logging(app):
    """Configure MiniMart logging for both the console and a local log file."""
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, None)

    if not isinstance(log_level, int):
        raise RuntimeError(
            "LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        )

    app_directory = Path(app.root_path).resolve()
    log_directory = (app_directory / "logs").resolve()
    configured_file = Path(app.config.get("LOG_FILE", "logs/app.log"))

    if configured_file.is_absolute():
        log_file = configured_file.resolve()
    else:
        log_file = (app_directory / configured_file).resolve()

    try:
        log_file.relative_to(log_directory)
    except ValueError as error:
        raise RuntimeError("LOG_FILE must point to a file under logs/.") from error

    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    for existing_handler in app.logger.handlers[:]:
        app.logger.removeHandler(existing_handler)
        existing_handler.close()

    app.logger.setLevel(log_level)
    app.logger.propagate = False
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.info(
        "Logging configured level=%s file=%s",
        level_name,
        log_file.name,
    )


def create_app(test_config=None):
    """Create and configure a MiniMart Flask application."""
    app = Flask(__name__)

    if test_config is None:
        app.config.update(load_config())
    else:
        app.config.update(test_config)

    configure_logging(app)

    app.add_url_rule("/", view_func=home)
    app.add_url_rule("/search", view_func=search)
    app.add_url_rule("/register", view_func=register, methods=["GET", "POST"])
    app.add_url_rule("/login", view_func=login, methods=["GET", "POST"])
    app.add_url_rule("/logout", view_func=logout)
    app.add_url_rule(
        "/cart/add/<int:product_id>",
        view_func=add_to_cart,
        methods=["POST"],
    )
    app.add_url_rule("/cart", view_func=cart)
    app.add_url_rule("/checkout", view_func=checkout, methods=["GET", "POST"])
    app.add_url_rule("/admin", view_func=admin)
    app.add_url_rule(
        "/admin/add",
        view_func=admin_add,
        methods=["GET", "POST"],
    )

    return app


def get_db():
    connection = sqlite3.connect(current_app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL CHECK (price >= 0)
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'shopper' CHECK (role IN ('shopper', 'admin'))
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
            [("Notebook", "A5 ruled notebook", 4.50), ("Water Bottle", "Reusable 750 ml bottle", 12.00), ("Wireless Mouse", "Compact USB mouse", 18.90), ("Desk Lamp", "LED study lamp", 24.50)],
        )
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [("admin", generate_password_hash("admin123"), "admin"), ("shopper", generate_password_hash("password1"), "shopper")],
        )
    connection.commit()
    connection.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return render_template("message.html", title="Not allowed", message="Administrator access is required.", category="danger"), 403
        return view(*args, **kwargs)
    return wrapped


def fetch_cart_products():
    ids = session.get("cart", [])
    if not ids:
        return []
    connection = get_db()
    placeholders = ",".join("?" for _ in ids)
    products = connection.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", ids).fetchall()
    connection.close()
    return products


def home():
    connection = get_db()
    products = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    connection.close()
    return render_template("index.html", products=products)


def search():
    term = request.args.get("q", "")
    connection = get_db()
    products = connection.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{term}%",)).fetchall()
    connection.close()
    return render_template("search.html", products=products, term=term)


def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("register.html"), 400
        connection = get_db()
        try:
            connection.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'shopper')", (username, generate_password_hash(password)))
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("That username is already registered.", "danger")
            return render_template("register.html"), 409
        connection.close()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        connection = get_db()
        user = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        connection.close()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


def logout():
    session.clear()
    return redirect(url_for("home"))


@login_required
def add_to_cart(product_id):
    ids = session.get("cart", [])
    ids.append(product_id)
    session["cart"] = ids
    return redirect(request.referrer or url_for("home"))


@login_required
def cart():
    products = fetch_cart_products()
    return render_template("cart.html", products=products, total=sum(p["price"] for p in products))


@login_required
def checkout():
    products = fetch_cart_products()
    total = sum(p["price"] for p in products)
    if request.method == "POST":
        if not products:
            flash("Your cart is empty.", "warning")
            return redirect(url_for("cart"))
        connection = get_db()
        connection.execute("INSERT INTO orders (username, total) VALUES (?, ?)", (session["username"], total))
        connection.commit()
        connection.close()
        session["cart"] = []
        return render_template("message.html", title="Order placed", message=f"Thank you. Your total is ${total:.2f}.", category="success")
    return render_template("checkout.html", count=len(products), total=total)


@admin_required
def admin():
    connection = get_db()
    products = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    connection.close()
    return render_template("admin.html", products=products)


@admin_required
def admin_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        try:
            price = float(request.form.get("price", ""))
        except ValueError:
            flash("Price must be a number.", "danger")
            return render_template("add_product.html"), 400
        if not name:
            flash("Product name is required.", "danger")
            return render_template("add_product.html"), 400
        if price < 0:
            flash("Price cannot be negative.", "danger")
            return render_template("add_product.html"), 400
        connection = get_db()
        connection.execute("INSERT INTO products (name, description, price) VALUES (?, ?, ?)", (name, description, price))
        connection.commit()
        connection.close()
        return redirect(url_for("admin"))
    return render_template("add_product.html")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        init_db()
    app.run(debug=True)
