# MiniMart Security Review

## Scope and context

MiniMart is a small internal Flask application with a SQLite database and a few hundred expected users. The review covers its catalogue, search, registration, authentication, cart, checkout and administrator functions, together with secrets, logging, tests and deployment controls.

“Internal” reduces exposure but does not remove the need for access control, password protection, safe database queries or recovery. This review is a point-in-time assessment, not a guarantee that every vulnerability has been found.

## Executive summary

The original application contained exploitable or high-impact weaknesses: SQL queries built from input, plaintext and hardcoded credentials, missing role checks, hardcoded secrets, raw HTML construction and swallowed exceptions. The hardened version materially improves these areas with parameterised SQL, password hashing, Jinja templates, role decorators, environment-based configuration and automated tests.

Important risks remain. MiniMart should not be represented as fully production-ready until known default credentials are removed, CSRF protection and login rate limiting are added, production execution is separated from Flask debug mode, and operational error handling and route-event logging are verified.

## Findings register

| ID | Finding | Risk | Evidence | Status |
|---|---|---|---|---|
| SEC-01 | SQL injection in input-driven queries | Critical in starter | Search input such as `' OR 1=1` could change query meaning. Current search and login use SQLite parameters. | Remediated for reviewed queries |
| SEC-02 | Plaintext and source-controlled passwords | Critical in starter | Starter accounts were defined in code. Current users table stores Werkzeug password hashes. | Remediated, but see SEC-08 |
| SEC-03 | Missing administrator authorization | High in starter | Login alone originally allowed access to admin functionality. `admin_required` now checks the session role and returns 403. | Remediated for current admin routes |
| SEC-04 | Stored or reflected HTML injection | High in starter | Pages were built with raw Python strings. Current output uses Jinja2 templates with normal auto-escaped expressions. | Remediated subject to template review |
| SEC-05 | Hardcoded Flask secret and database configuration | High in starter | `SECRET_KEY` was in source. Current `load_config()` requires environment values and fails closed when absent. | Remediated if production secret is private |
| SEC-06 | Silent exception handling | High | Bare `except` blocks hid database and query failures. | Silent catches removed; safe error handling still requires verification |
| SEC-07 | Missing CSRF protection | High | State-changing POST routes accept requests without an anti-CSRF token. | Open |
| SEC-08 | Known seeded administrator and shopper credentials | High | `init_db()` creates accounts using publicly known training passwords when the table is empty. Hashes do not protect known passwords. | Open; must not ship unchanged |
| SEC-09 | No login rate limit or account lockout | High | Repeated password attempts are not slowed or blocked. | Open |
| SEC-10 | Flask development server/debug mode available | High if used in production | Direct execution ends with `app.run(debug=True)`. | Mitigated only when production uses Gunicorn/systemd |
| SEC-11 | Incomplete price validation | Medium | `float()` can accept non-finite values such as infinity; `NaN` may cause an uncontrolled database failure. | Open |
| SEC-12 | Session authorization can become stale | Medium | Username and role are copied into the signed session rather than reloaded for privileged operations. | Open |
| SEC-13 | Cart identifier validation is missing | Medium | Any integer product ID can be added without confirming that a product exists. | Open |
| SEC-14 | Logging may not contain all agreed route events | Medium | Logging setup exists, but every login, denial, order and admin event must be verified in the deployed release. | Verify before relying on alerts |
| SEC-15 | Logout changes state through GET | Low | An external page can cause a user to be logged out. | Open |
| SEC-16 | Weak password acceptance | Medium | Empty passwords are rejected, but whitespace-only and weak passwords are not. | Open |
| SEC-17 | SQLite file protection and backup ownership | Medium | Anyone who can read the database file can obtain user hashes and business data. | Operational control required |

## OWASP-oriented summary

| OWASP area | MiniMart evidence | Position |
|---|---|---|
| Broken Access Control | `admin_required` blocks shoppers on both page views and POST actions. Stale session roles and CSRF remain. | Improved; residual risk |
| Cryptographic Failures | Passwords are hashed and `SECRET_KEY` is externalised. Known seeded passwords remain unsafe. | Improved; default credentials must be removed |
| Injection | Reviewed login and search SQL is parameterised; templates replace raw HTML building. | Strong improvement |
| Insecure Design | Orders lack line items and recovery assumptions are limited. Abuse controls are absent. | Further design work needed |
| Security Misconfiguration | Required configuration fails closed, but debug mode and production cookie settings require attention. | Partially controlled |
| Vulnerable and Outdated Components | Dependencies are installed by the pipeline, but no vulnerability or update check is documented. | Not evidenced |
| Identification and Authentication Failures | Hash verification and generic login errors exist; rate limiting and a strong password policy do not. | Partially controlled |
| Software and Data Integrity Failures | GitHub Actions runs tests on pushes and pull requests. Dependency provenance and protected-branch enforcement are not evidenced. | Partially controlled |
| Security Logging and Monitoring Failures | Safe logging setup and alert thresholds are designed. Route-event implementation and alert delivery must be verified. | Partially controlled |
| Server-Side Request Forgery | MiniMart currently makes no reviewed server-side requests to user-supplied URLs. | Not applicable to current scope |

## Implemented control evidence

### Database query safety

Input values are passed separately from SQL text:

```python
connection.execute(
    "SELECT * FROM users WHERE username = ?",
    (username,),
)
```

The search route follows the same parameterised pattern.

### Password storage

Registration uses `generate_password_hash()` and authentication uses `check_password_hash()`. The test suite verifies that the stored value differs from the submitted password and validates correctly through Werkzeug.

### Authorization

`login_required` protects cart and checkout functions. `admin_required` checks both authentication and `role == "admin"`. Tests submit `GET /admin`, `GET /admin/add` and `POST /admin/add` as a shopper and expect HTTP 403 with no product inserted.

### Secrets and configuration

Production values are expected outside the repository:

```text
SECRET_KEY=<private random value>
DATABASE_PATH=/var/lib/minimart/minimart.db
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

`.env`, database files and `logs/` must be excluded from Git. Production should use a protected systemd environment file such as `/etc/minimart/minimart.env`, not a committed `.env` file.

### Delivery control

The GitHub Actions workflow installs dependencies and runs `pytest` on pushes and pull requests targeting `main`. This is evidence of a regression gate, not proof that the tests cover every vulnerability.

### Recovery control

The rollback plan defines two measurable triggers, a five-minute decision window, exact commands and verification. It explicitly does not claim that reverting application code reverses data already written to SQLite.

## Required actions before production use

### Must complete

1. Remove known seeded credentials from production initialization.
2. Create the initial administrator through a controlled process with a private password.
3. Add CSRF protection to registration, cart, checkout, logout and admin changes.
4. Add proportionate login rate limiting and test it.
5. Reject non-finite and unreasonably large prices.
6. Ensure production runs through Gunicorn/systemd, never `python app.py`.
7. Confirm `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY` and an appropriate `SESSION_COOKIE_SAMESITE` policy in production.
8. Confirm every agreed security and business event is logged without secrets.
9. Protect `/etc/minimart/minimart.env`, `minimart.db`, backups and logs with least-privilege filesystem permissions.
10. Rehearse backup restoration and application rollback.

### Should complete

- Validate product existence before adding to the cart.
- Store user IDs and order lines rather than only username and total.
- Re-check current administrator role for privileged actions.
- Add controlled error handlers that return safe user messages while recording a traceable server error.
- Pin and review dependencies; document an update process.
- Restrict production repository and deployment access to the small responsible team.

## Never log

- Passwords, password confirmation values or password hashes
- Starter credentials or credential-reset values
- `SECRET_KEY`, API keys, access tokens or `.env` contents
- Session cookies, signed cookie values or the complete Flask `session`
- `Cookie`, `Authorization` or other authentication headers
- Complete request bodies or form dictionaries
- Raw login or registration fields
- Raw search terms; record only safe metadata such as length and result count
- Raw product descriptions or complete administrator submissions
- Full cart contents, complete database rows or SQL parameters
- Database dumps or the contents of `minimart.db`
- Exception output containing submitted values, secrets or database records
- Future payment-card, bank-account or security-code data

## Claims this review does not support

- MiniMart is completely secure.
- Every vulnerability has been found.
- A green pipeline proves the release is safe.
- Password hashing makes known default passwords acceptable.
- An internal application does not need CSRF or brute-force protection.
- An 80% coverage result means 80% of security requirements are verified.
- Rollback restores the database to its previous state.

## Review conclusion

The security posture improved because the work addressed specific, demonstrated weaknesses and added tests around critical authentication and authorization behaviour. The application still carries material, named risks. Approval for production should depend on closing the must-complete actions and rehearsing the operational controls rather than on the five-day build speed.
