# Security Review

## Fixed in Lab 2

- Passwords are hashed with Werkzeug and stored in SQLite.
- Protected routes use `login_required` and `admin_required`.
- `SECRET_KEY` and `DATABASE_PATH` are loaded from environment variables.

## Known limitations intentionally retained

- Login has no rate limiting.
- Forms do not include CSRF tokens.
- Password-strength rules are minimal for this teaching app.

## AI review versus manual review

Complete this section during the practical activity: what the AI found, what you found by hand, why the gap occurred, and the human safeguard you recommend.
