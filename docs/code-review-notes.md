# MiniMart Code Review Notes

## Scope

This review follows MiniMart from the deliberately flawed starter application to the hardened Flask application. It records what was found, what changed, what evidence supports the change and what remains unresolved.

The current application contains these routes:

| Route | Method | Purpose | Protection expected |
|---|---|---|---|
| `/` | GET | Product catalogue | Public |
| `/search` | GET | Product search | Public |
| `/register` | GET, POST | Shopper registration | Public |
| `/login` | GET, POST | Authentication | Public |
| `/logout` | GET | End session | Logged-in session preferred |
| `/cart/add/<product_id>` | POST | Add an item to the cart | Logged-in user |
| `/cart` | GET | Display cart | Logged-in user |
| `/checkout` | GET, POST | Review and place order | Logged-in user |
| `/admin` | GET | Administrator catalogue | Administrator |
| `/admin/add` | GET, POST | Add a product | Administrator |

## Review approach

The review used behaviour tests rather than relying only on reading the code. Important probes included:

- SQL-injection-style search and login input
- HTML input such as `<b>hello</b>`
- A shopper browsing directly to `/admin`
- Invalid administrator prices such as `abc` and `-1`
- Empty and nonexistent search terms
- Registration and authentication failure paths
- Direct POST requests to administrator endpoints

## Findings and changes

| Finding | Original risk | Change made | Current evidence/status |
|---|---|---|---|
| SQL built by string concatenation | Search or login input could alter the SQL query. | Replaced user-value concatenation with SQLite parameter placeholders. | `search()` and `login()` use `?` parameters. Resolved for reviewed queries. |
| HTML built with Python strings | Product or search values could be returned as executable markup. | Moved page output into Jinja2 templates. | Flask auto-escaping applies when templates use normal `{{ value }}` output. Resolved, subject to template review. |
| Plaintext passwords and in-code `USERS` dictionary | Anyone reading source or database content could recover credentials. | Added a `users` table and Werkzeug password hashing. | Registration stores `password_hash`; login uses `check_password_hash()`. Improved. |
| Hardcoded Flask secret | A public repository could expose the session-signing secret. | Added environment-based configuration with fail-fast validation. | `SECRET_KEY` and `DATABASE_PATH` are loaded outside source. Resolved if production secret handling is correct. |
| Authentication used as authorization | A logged-in shopper could reach administrator functions. | Added separate `login_required` and `admin_required` decorators. | Tests cover shopper denial for GET and POST admin paths. Resolved for current routes. |
| Bare `except` blocks | Database and query failures disappeared silently, hiding data and availability problems. | Removed silent exception handling and designed explicit logging/error handling. | Silent catches are removed. Controlled database-error responses still need verification. |
| Invalid product prices | Text or negative values could crash the route or corrupt product data. | Added numeric parsing, negative-value rejection and a database `CHECK`. | Tests cover `abc` and `-1`. Partially resolved because non-finite values remain. |
| Duplicate usernames | Two accounts could share an identity or registration could fail unclearly. | Added `UNIQUE` constraint and a controlled HTTP 409 response. | Registration tests verify the response and row count. Resolved. |
| Empty checkout | The application could create a false order. | Reject empty carts and redirect with a warning. | Edge-case test verifies no order row is created. Resolved. |
| Configuration and logs in the repository | Secrets, database data and operational logs could be committed. | Added `.env`, `*.db`, `logs/` and virtual-environment exclusions. | Must be checked with `git check-ignore` before every first push or repository move. |
| Flask global application structure | Tests could not reliably inject temporary configuration and databases. | Added `create_app(test_config=None)`. | Test fixtures can create isolated app instances. Resolved. |

## Important current weaknesses

| Priority | Weakness | Where | Production consequence | Recommended action |
|---|---|---|---|---|
| High | Known default accounts are seeded when the user table is empty. Hashing does not make a publicly known password safe. | `init_db()` | A fresh production database may contain immediately guessable administrator credentials. | Do not seed production users. Create the first administrator through a controlled one-time process and force a private password. |
| High | No CSRF protection on state-changing forms. | Registration, cart add, checkout and admin add | Another site could submit requests using an authenticated user's browser. | Add CSRF tokens before public or less-trusted use. |
| High | No login rate limiting or lockout. | `/login` | Automated password guessing can continue without an application-side limit. | Add proportionate rate limiting and monitor repeated failures. |
| High | `app.run(debug=True)` remains in the direct-run block. | End of `app.py` | Running this command in production exposes the development server and possibly debugger behaviour. | Run production only through Gunicorn/systemd; make debug mode opt-in for local development. |
| Medium | `float()` accepts `NaN` and infinity. | `admin_add()` | Invalid values may cause database errors or unusable prices. | Reject values for which `math.isfinite(price)` is false and set a sensible upper bound. |
| Medium | Duplicate product IDs in the session are collapsed by `WHERE id IN (...)`. | `fetch_cart_products()` | Adding the same product twice may be charged only once. | Store quantities explicitly or reconstruct results without losing duplicate IDs. |
| Medium | A nonexistent product ID can be stored in the session. | `add_to_cart()` | The cart may contain fabricated or deleted product references. | Query the product before adding it and return 404 or a controlled message when absent. |
| Medium | Database connections are manually closed only on successful paths. | Multiple routes | Exceptions can leave connections open and produce locks or resource leaks. | Use context managers or `try/finally` consistently. |
| Medium | An order stores only username, total and timestamp. | `orders` table | There is no immutable record of product lines, quantities or prices at purchase time. | Add order-line records and a user foreign key before relying on MiniMart for financial reconciliation. |
| Medium | Role information is copied into the signed session. | `login()` and decorators | A role changed in the database may remain active until the user signs in again. | Store a stable user ID and re-check current role for privileged actions. |
| Medium | Route-level event logging is not evident in the reviewed application file. | Authentication, checkout and admin routes | Monitoring based on event counts may have no reliable source. | Confirm the deployed branch contains the agreed safe logging calls and tests for them. |
| Low | The Admin navigation link is visible to shoppers. | `base.html` | Access is blocked server-side, but the interface is confusing and invites unnecessary denial events. | Render the link only when `session.role == 'admin'`; retain server-side checks. |
| Low | Logout uses GET. | `/logout` | Third-party content can trigger logout, although it cannot take over the session. | Change logout to POST with CSRF protection. |
| Low | Passwords containing only spaces are accepted. | `/register` and `create_user.py` | Accounts can be created with extremely weak credentials. | Define and test a proportionate password policy. |

## Query safety note

The following query contains an f-string but is not currently user-controlled SQL concatenation:

```python
placeholders = ",".join("?" for _ in ids)
connection.execute(
    f"SELECT * FROM products WHERE id IN ({placeholders})",
    ids,
)
```

The f-string inserts only generated `?` placeholders; values remain separate parameters. It should still be reviewed if the placeholder construction changes.

## Review decisions that should remain explicit

- Authentication answers “Who is this user?” Authorization answers “May this user perform this action?” Both are required.
- A hidden Admin button is not an access-control mechanism. The server-side decorator is the control.
- Password hashes and session signatures reduce risk but do not compensate for known default passwords or a leaked secret key.
- A working page is not proof that failure paths are controlled.
- A parameterised query prevents input from becoming SQL syntax; it does not validate whether the business value is sensible.
- AI-generated changes must be small enough for a person to explain and review before committing.

## Before accepting another generated change

1. State the behaviour that should change.
2. Identify the exact route, function and data affected.
3. Review the diff; reject unrelated restructuring.
4. Add or update a test that fails without the change.
5. Run the focused test file.
6. Run the complete suite.
7. Check that secrets, logs, the database and virtual environment are not staged.
8. Record the prompt and decision in `prompts/prompt-log.md`.
9. Commit one coherent change with a specific message.
10. Confirm the GitHub Actions pipeline passes.

## Current conclusion

MiniMart is substantially safer than the starter application because the reviewed injection, output-encoding, password-storage, configuration and role-enforcement failures were addressed. It should not be described as completely secure or fully production-ready while default credentials, CSRF, rate limiting, non-finite prices, incomplete order records and operational error handling remain open.

