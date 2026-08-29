# MiniMart Logging and Monitoring Plan

## Scope and operating model

MiniMart is a small internal application with a few hundred users and no dedicated operations team. Monitoring should wake someone only for service loss or loss of the order-writing path. Other useful signals belong on a simple dashboard or working-hours review.

Use Python's built-in logging to write the same structured events to the console and `logs/app.log`. The log level comes from the production environment. Do not duplicate routine page views already present in the HTTP access log.

## Log levels

| Level | Use in MiniMart |
|---|---|
| `DEBUG` | Diagnostic detail such as query duration and result count; normally disabled in production. |
| `INFO` | Successful business or security-relevant events. |
| `WARNING` | Rejected, suspicious or invalid activity that did not crash the application. |
| `ERROR` | A requested operation failed unexpectedly. |
| `CRITICAL` | MiniMart cannot start or cannot initialize a required dependency. |

Each event should include a stable event name plus safe context such as timestamp, request ID, numeric user ID or safe username, role, route, method, product ID, order ID and outcome. Never log the complete request or session.

## Events to log

| Event | Log level | Incident question answered |
|---|---|---|
| Application starts with environment and version | INFO | Which version and environment are actually running? |
| Required configuration is missing | CRITICAL | Why did MiniMart fail to start? |
| Database initialization succeeds | INFO | Was the database prepared before requests started? |
| Database initialization fails | CRITICAL | Is the entire service unavailable because tables could not be prepared? |
| Registration succeeds | INFO | Was this account created successfully, and when? |
| Registration rejects missing fields | WARNING | Are failures caused by bad input or automated requests? |
| Registration rejects an existing username | WARNING | Are duplicate attempts increasing or affecting a specific account? |
| Registration database operation fails | ERROR | Why could a valid account not be created? |
| Login succeeds | INFO | Did this account authenticate before the reported activity? |
| Login fails for a wrong password or unknown username | WARNING | Are failures ordinary mistakes or repeated password guessing? |
| Logout succeeds | INFO | Did the user's session end when Logout was selected? |
| Logged-out user requests a protected route | INFO | Was the redirect caused by an expired or missing session? |
| Shopper is denied an administrator route, including POST | WARNING | Which account attempted a privileged action without permission? |
| Search completes | DEBUG | Was search slow, and how many results did it return? |
| Product query fails | ERROR | Is SQLite locked, unavailable or rejecting queries? |
| Product is added to cart | INFO | Was this product accepted before the user reported a missing item? |
| Cart contains a nonexistent product ID | WARNING | Is the session referencing a deleted or fabricated product? |
| Cart count and total are calculated | DEBUG | What count and total did the server calculate before checkout? |
| Empty checkout is rejected | WARNING | Why was checkout refused, and are rejections increasing? |
| Order is placed | INFO | Was an order stored, for which user and order ID? |
| Order insertion fails | ERROR | Did checkout fail because the order could not be written? |
| Invalid product submission is rejected | WARNING | Why was the administrator submission refused? |
| Administrator creates a product | INFO | Which administrator changed the catalogue and which product ID was created? |
| Product insertion fails | ERROR | Why did a valid-looking administrator request fail? |
| Unexpected exception reaches the error handler | ERROR | Which operation crashed and which request should be traced? |
| Command-line user creation succeeds | INFO | Was the account created through `create_user.py` rather than registration? |
| Command-line administrator creation succeeds | WARNING | When and through which controlled process was privileged access created? |
| Repeated authentication or authorization failures cross a threshold | WARNING | Is this one mistake or automated hostile activity? |

## Recommended safe event structure

```text
2026-08-29T10:30:00+0000 | INFO | app | event=login_success actor=shopper role=shopper outcome=success
2026-08-29T10:32:00+0000 | WARNING | app | event=admin_access_denied actor=shopper role=shopper method=POST route=/admin/add
2026-08-29T10:35:00+0000 | INFO | app | event=order_placed actor=shopper order_id=12 item_count=1 outcome=success
```

Use event names and identifiers, not free-form dumps of request objects.

## Never log

- Passwords entered during registration, login or `create_user.py`
- Password confirmations, password hashes, salts or starter passwords
- `SECRET_KEY`, API keys, access tokens or `.env` contents
- Session cookies, signed cookie values or the complete Flask `session`
- `Cookie`, `Authorization` or other authentication headers
- Complete request bodies or form dictionaries
- Raw login or registration fields
- Raw search terms; log term length and result count instead
- Raw product names or descriptions submitted through `/admin/add`
- Full cart contents; use item count and safe IDs only where necessary
- Complete database rows, database dumps or SQL parameter values
- The contents of `minimart.db`
- Full filesystem paths when they unnecessarily reveal server structure
- Raw exception output containing submitted data, environment values or records
- Personal identifiers when an internal numeric ID can answer the same question
- Future payment-card, bank-account or security-code information

## Metrics and alert policy

| Metric | Why it matters | Alert or dashboard | Threshold |
|---|---|---|---|
| Application availability | If the home or login page cannot be returned, users cannot use MiniMart. | **Wake-up alert 1** | Alert after **3 consecutive failed checks, one minute apart**. **False alarm:** a planned restart or a temporary network failure between the checker and a healthy app. |
| Order/database write failures | Repeated failures can lose business transactions and may indicate a lock, full disk or database corruption. | **Wake-up alert 2** | Alert when **3 order-write errors occur within 10 minutes**, or when **all checkout attempts fail with at least 3 attempts**. **False alarm:** one test user repeatedly checking out against a deliberately unavailable test database, or repeated clicks during a planned restart. |
| Request count and response time by route | Shows whether search, cart, checkout or admin pages are becoming slow or unusually busy. | Dashboard only | Display request count and p95 response time in 15-minute intervals. Review during working hours if p95 remains above about **2 seconds**. |
| Successful and failed logins plus admin denials | Reveals forgotten passwords, authentication problems or suspicious administrator probes. | Dashboard only | Display hourly totals and the failure-to-success ratio. Review spikes during working hours; training and password changes can cause legitimate spikes. |
| Orders placed, empty-checkout rejections and products added | Shows whether core workflows are being used and completed. | Dashboard only | Display hourly and daily totals. Do not alert on low activity because an internal app may be unused overnight, on weekends or during holidays. |

Exactly two conditions are wake-up alerts. Login spikes, low order volume and slower responses are useful but not proportionate reasons to wake someone for this application.

## Alert ownership and response

- The named MiniMart application owner receives both wake-up alerts.
- The backup is the nominated team lead; there is no separate operations rota.
- An alert must include time, environment, route or operation, threshold breached and a link to relevant logs.
- During or immediately after deployment, the responder follows [deployment-rollback.md](deployment-rollback.md).
- The Deployment Owner has five minutes from alert receipt to decide whether the release should be rolled back.
- A database-write alert requires preservation of the current database before any recovery attempt.

## Logging verification sequence

Add and test event calls in this order so defects are isolated:

### 1. Registration, login and logout

| Action | Expected result | Expected event |
|---|---|---|
| Register a new user | Redirect to login; account exists with hash | `INFO event=registration_success` |
| Register duplicate username | HTTP 409; no duplicate row | `WARNING event=registration_rejected reason=duplicate_username` |
| Correct login | Redirect home; session created | `INFO event=login_success` |
| Correct username, wrong password | Generic rejection; no session | `WARNING event=login_failed` |
| Logout | Redirect home; session cleared | `INFO event=logout` |

### 2. Shopper blocked from administrator routes

Test `GET /admin`, `GET /admin/add` and `POST /admin/add`. Each must return HTTP 403, perform no insertion and create one `WARNING event=admin_access_denied` containing actor, role, method and route.

### 3. Order placed

Log in, add one product and submit checkout. Confirm one order is created, the cart clears and one `INFO event=order_placed` includes safe user identifier, order ID and item count. Empty checkout should create `WARNING event=checkout_rejected reason=empty_cart` and no order.

### 4. Administrator adds a product

Submit one valid product and verify exactly one row plus `INFO event=product_created`. Submit `abc` and `-1`; each must return HTTP 400, insert nothing and create a safe warning without raw product data.

### 5. Unexpected errors

Using a temporary test database, force a database operation to raise `sqlite3.OperationalError`. Confirm a safe HTTP 500 response, one `ERROR` event with operation, route, method and stack trace, no secret or form body, and continued handling of later requests where possible.

## Privacy verification

For every event group, confirm:

1. The application still behaves correctly.
2. The event appears once in both the console and `logs/app.log`.
3. The level and safe context are correct.
4. No password, hash, token, cookie, request body or session appears.

On Windows PowerShell during local testing:

```powershell
Get-Content .\logs\app.log -Wait
Select-String -Path .\logs\app.log -Pattern "YOUR_TEST_PASSWORD"
```

The password search must return no output. Duplicate ordinary events indicate duplicate logging handlers and must be corrected.

## Proportionate implementation

MiniMart does not need a large observability platform. A proportionate setup consists of:

- systemd supervision and its journal
- the structured local application log under `logs/`
- log rotation with an agreed retention period
- one external or separate-host HTTP availability check every minute
- a small scheduled parser or existing lightweight monitor that counts `order_write_error` events in a rolling 10-minute window
- one working-hours dashboard for route latency, login outcomes and business-event totals

The availability check must run outside the MiniMart process; an application cannot reliably report that it is unavailable.

## Evidence and limitations

- Logging configuration is not evidence that every route emits its agreed event. Exercise each route and inspect the log.
- The absence of errors is not proof of health when there is no traffic. Use the availability probe and a controlled checkout after deployment or rollback.
- Logs explain what the application recorded; they may be incomplete if a process crashes before flushing or the disk is full.
- Monitoring detects defined symptoms. It does not prevent incidents or prove their cause.
- Alert thresholds should be reviewed after several weeks of real traffic, but changes must be documented rather than adjusted merely to silence alerts.
