# MiniMart Testing Notes

## Purpose

The MiniMart suite is a regression safety net for a small Flask application. It demonstrates selected behaviours; it does not prove that every requirement is correct, every security control is sufficient or every production failure has been anticipated.

## Test categories

| Category | Beginner definition | MiniMart examples |
|---|---|---|
| Unit test | Tests one small function or decision in isolation. | Configuration validation, password helpers or a price-validation helper if extracted. |
| Integration test | Exercises several parts together, such as route, session, template and temporary database. | Registration, login, checkout and administrator product creation. |
| Edge-case test | Exercises unusual, invalid or boundary input. | Empty cart, duplicate username, negative price, text price and unauthorized POST. |

Most current MiniMart tests are integration or edge-case tests because they use Flask's test client and a temporary SQLite database.

## Test environment

Every test should receive a new temporary database through `tests/conftest.py`:

```python
test_app = create_app(
    {
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "DATABASE": str(database_path),
        "LOG_LEVEL": "WARNING",
        "LOG_FILE": "logs/test.log",
    }
)
```

This prevents tests from using `.env`, `minimart.db` or the normal application log. Test credentials and the test-only secret must never be reused in production.

## Current suite inventory

| File | Collected tests | What it verifies |
|---|---:|---|
| `tests/test_smoke.py` | 5 | Catalogue, search, successful shopper login, logged-out cart redirect and shopper denial from `/admin`. |
| `tests/test_auth.py` | 10 | Registration, password hashing, forced shopper role, missing fields, duplicate usernames, successful login, failed login and logout. |
| `tests/test_edge_cases.py` | 8 | Empty checkout, negative and non-numeric prices, duplicate registration, three shopper/admin route-method combinations and correct username with wrong password. |
| **Total expected collection** | **23** | The parameterised administrator test is collected as three cases. |

Confirm the actual total rather than relying on this document:

```bash
pytest --collect-only -q
pytest -q
```

## Edge-case expectations

| Case | Expected application behaviour | Behaviour represented by the current tests |
|---|---|---|
| Empty checkout | Redirect to `/cart`, show an empty-cart warning and create no order. | Test asserts redirect, message and zero order rows. |
| Negative product price | Return HTTP 400, show `Price cannot be negative` and insert no product. | Test asserts all three outcomes. |
| Non-numeric product price | Return HTTP 400, show `Price must be a number` and insert no product. | Test asserts all three outcomes. |
| Duplicate username | Return HTTP 409, show the duplicate message and retain exactly one account. | Test compares row counts before and after. |
| Shopper accessing admin routes | Return HTTP 403 for `GET /admin`, `GET /admin/add` and `POST /admin/add`; perform no insertion. | One parameterised test covers all three combinations. |
| Correct username with wrong password | Show a generic error and create no authenticated session. | Test checks message and absence of username and role. |

No test should be written to preserve behaviour known to be defective. Record the expected behaviour first; if the application differs, make the test expose the defect.

## Running the suite

Run focused files while developing:

```bash
pytest tests/test_smoke.py -v
pytest tests/test_auth.py -v
pytest tests/test_edge_cases.py -v
```

Run the complete suite before committing:

```bash
pytest
```

If `pytest-cov` is installed, inspect uncovered lines:

```bash
pytest --cov=app --cov-report=term-missing
```

Do not add a coverage package only to produce a more impressive percentage. Use missing-line information to decide which important behaviour lacks evidence.

## Why 80% coverage can be misleading

Coverage measures which Python lines happened to execute. It does not measure whether the assertions were meaningful, requirements were correct or security controls were adequate.

### Covered but not verified

- `init_db()` executes before tests, so schema and seed lines count as covered. The suite may not verify every constraint, idempotency or duplicate-seed behaviour.
- Every `app.add_url_rule()` executes when the fixture calls `create_app()`. That does not prove that every URL has the intended HTTP methods.
- The catalogue test checks for `Notebook`, but not that every product appears, ordering is correct or stored HTML is escaped.
- The search test uses only `Mouse`; it does not verify injection input, wildcard behaviour, HTML input or an empty query.
- Administrator login runs during invalid-price tests, covering the successful branch of `admin_required`, without proving that a valid product can be added successfully.
- The empty-checkout test covers the rejection branch but not successful total calculation, order insertion and cart clearing.
- `get_db()` and connection setup run repeatedly, but coverage does not prove connections close during every exception path.
- A Python `render_template()` call may be covered while generated HTML, form fields, links, escaping and missing variables remain unverified.

### Not caught by any current test

- Adding the same product twice may count it once because `WHERE id IN (...)` collapses duplicate IDs.
- A nonexistent product ID can be added to the session.
- No current saved test completes a successful purchase and verifies username, total, timestamp and cart clearing.
- No current saved test submits a valid product and confirms the stored values.
- No test proves an administrator can successfully open both administrator pages.
- Search injection-style, wildcard and HTML inputs are not covered by the current saved suite.
- Product prices such as `NaN`, infinity and extremely large numbers are not tested.
- Registration accepts a password containing only spaces.
- Login rate limiting, account lockout and password strength are not tested because the controls do not exist.
- CSRF is not tested because the application has no CSRF control.
- The suite relies on known seed credentials, normalising a production security weakness.
- Fixtures pass configuration directly to `create_app()`, bypassing production `.env` loading.
- Database locks, missing files, full disks and failed queries are not exercised.
- `create_user.py` role validation, duplicate handling and administrator creation are outside the current suite.
- Dependency installation and operating-system differences may fail only in CI or deployment.

## Highest-priority next tests

| Priority | Test to add | Outcome to verify |
|---|---|---|
| High | Successful checkout | One order is created with the correct user and total; the cart clears. |
| High | Successful administrator product creation | Exactly one valid product is stored and displayed. |
| High | Search injection and escaping | Input remains data, does not return unintended rows and is escaped in HTML. |
| High | Non-finite and huge prices | Request is rejected and no product is inserted. |
| High | Database write failure | Safe HTTP response, `ERROR` log and no partial transaction. |
| Medium | Duplicate cart quantities | Quantity and total match repeated additions. |
| Medium | Nonexistent product ID | Controlled 404/message and unchanged cart. |
| Medium | Production configuration validation | Missing secret/database path fails without disclosing values. |
| Medium | Logging privacy | Required event appears once; password, hash, cookie and session do not appear. |
| Medium | `create_user.py` | Valid roles succeed; invalid role, weak password and duplicate user fail safely. |

## GitHub Actions gate

The workflow `.github/workflows/ci.yml` runs on pushes and pull requests targeting `main`:

1. Check out the repository.
2. Install Python 3.10.
3. Install `requirements.txt`.
4. Run `pytest`.
5. Return a non-zero job status when a test or fixture fails.

The pipeline has already exposed test-environment problems, including tests requesting a nonexistent `login_as` fixture and logging setup depending on inappropriate configuration. That is evidence the pipeline can block known failure types. It is not evidence that it can detect missing requirements or untested behaviour.

## Pipeline troubleshooting record

| Symptom | Cause | Resolution |
|---|---|---|
| `fixture 'login_as' not found` | Test function declared `login_as` as a fixture even though no fixture existed. | Use a normal login helper and request only the existing `client` fixture. |
| Every smoke test fails during setup | `create_app()` failed while test logging/configuration was initialized. | Supply test-only `LOG_LEVEL` and `LOG_FILE` in `conftest.py`. |
| Tests pass locally but fail in CI | Common causes include missing dependency, different Python version or hardcoded path. | Reproduce with the pipeline Python version and keep fixtures path-independent. |
| `ModuleNotFoundError: app` | Repository root is not on pytest's import path. | Keep `pythonpath = .` in `pytest.ini` or use a proper package layout. |
| Workflow does not run | File path or YAML structure is wrong. | Use exactly `.github/workflows/ci.yml` and spaces, not tabs. |

## Definition of done for a MiniMart change

- Expected behaviour is written before the test.
- The focused test fails without the intended fix.
- The focused test passes after the fix.
- The complete suite passes locally.
- No production secret, log, database or virtual environment is staged.
- The commit contains one coherent change.
- GitHub Actions passes for the exact commit intended for deployment.
- Coverage changes are explained by behaviour, not presented as proof of correctness.

## Claims to avoid

- “Twenty-three tests cover every route and failure.”
- “Eighty per cent coverage means the app is eighty per cent correct.”
- “A green pipeline proves MiniMart is secure.”
- “Generated tests are independent evidence if they merely repeat generated implementation assumptions.”
- “Passing locally guarantees production success.”

