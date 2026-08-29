# MiniMart Deployment and Rollback Plan

## Scope

MiniMart is a small internal Flask application with one SQLite database, a few hundred users, one small team and no dedicated operations staff. The chosen deployment method is a **simple controlled restart** of one production instance.

This runbook assumes:

- Ubuntu/Linux production server
- Repository checkout: `/opt/minimart`
- Python environment: `/opt/minimart/.venv`
- systemd service: `minimart`
- Gunicorn address: `127.0.0.1:8000`
- Production database: `/var/lib/minimart/minimart.db`
- Protected environment file: `/etc/minimart/minimart.env`
- Application log: `/opt/minimart/logs/app.log`
- Database backups: `/var/backups/minimart`
- Known-good rollback tag in the example: `v1.0`

Change these paths once if the real server uses different locations, then rehearse the resulting commands. Do not improvise paths during an incident.

## Deployment strategy comparison

| Strategy | Fit for MiniMart | SQLite and team impact | Cost and trade-off |
|---|---|---|---|
| Blue-green | Poor fit: it duplicates the entire small application to avoid a short restart. | Separate SQLite copies would diverge, while sharing one local database file across hosts is unsuitable. | Additional environment, routing and migration work; code rollback is fast, but database writes are not reversed. |
| Canary | Worst fit: a few hundred internal users produce too little traffic for reliable canary evidence. | Requires concurrent versions, traffic splitting, detailed metrics and someone available to interpret them. SQLite remains a blocker. | Highest operational complexity for little practical risk reduction. |
| Simple controlled restart | Best fit: deploy a tested commit during a short maintenance window and restart one service. | Keeps one application service writing to one SQLite database, matching the current architecture and team. | Brief downtime, interrupted requests and a manual rollback; a database backup is required before schema work. |

## Recommendation

Use a simple controlled restart because MiniMart's internal audience, single SQLite database and small team make parallel strategies more dangerous than a short maintenance window. The cost is a few minutes of downtime, interruption of active requests and reliance on a tested rollback procedure plus a pre-deployment database backup. Blue-green or canary becomes credible only after MiniMart needs near-zero downtime, uses a concurrent server database such as PostgreSQL, runs stateless instances behind a load balancer, supports backward-compatible migrations and has enough monitoring, traffic and operational ownership to judge a partial release.

## Production process model

Production must run through Gunicorn under systemd, not through:

```bash
python app.py
```

The direct command starts Flask's development server and the current code enables debug mode. That server is intended for local development, does not provide the same process supervision and graceful restart behaviour, and must not be exposed as the production service.

The systemd service should use an execution command equivalent to:

```ini
[Unit]
Description=MiniMart Gunicorn service
After=network.target

[Service]
User=minimart
Group=minimart
WorkingDirectory=/opt/minimart
EnvironmentFile=/etc/minimart/minimart.env
ExecStart=/opt/minimart/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 "app:create_app()"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Two workers are proportionate for this small application, but SQLite serialises writes. If write-lock errors appear, reduce concurrency or move to a server database rather than adding more workers.

## Production environment variables

Production variables come from `/etc/minimart/minimart.env`, referenced by systemd. They do not come from GitHub, the repository or a committed `.env` file.

Expected keys:

```text
SECRET_KEY=<private-random-production-value>
DATABASE_PATH=/var/lib/minimart/minimart.db
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

Protect the file:

```bash
sudo chown root:minimart /etc/minimart/minimart.env
sudo chmod 640 /etc/minimart/minimart.env
```

Never print the file during deployment or paste its contents into a ticket, log or screenshot.

## Pre-deployment requirements

Do not begin the restart until all of the following are true:

- The intended commit is on `main`.
- The MiniMart CI workflow passed for that exact commit.
- The release commit or current known-good commit has a tag.
- The maintenance window has been communicated.
- The application owner and rollback decision-maker are available.
- The production worktree is clean.
- There is sufficient disk space for a database backup.
- Any schema change has a tested, backward-compatibility and recovery decision.

## Controlled deployment commands

### 1. Open the production checkout

```bash
cd /opt/minimart
```

This ensures every later Git and environment command targets MiniMart.

### 2. Fetch the tested branch and tags

```bash
sudo -u minimart git fetch origin main --tags
```

This updates remote information without changing the running checkout.

### 3. Confirm the worktree is clean

```bash
sudo -u minimart git status --short
```

Expected result: no output. Stop if files are shown; switching releases could otherwise overwrite or mix uncommitted production changes.

### 4. Record the current release

```bash
sudo -u minimart git rev-parse HEAD | sudo tee /var/lib/minimart/previous-release.txt > /dev/null
sudo cat /var/lib/minimart/previous-release.txt
```

This preserves the exact commit to which the code can be returned. Recording the wrong commit makes rollback ambiguous.

### 5. Stop MiniMart

```bash
sudo systemctl stop minimart
sudo systemctl is-active minimart
```

Expected result: `inactive`. Requests in progress may fail; this is the planned downtime point.

### 6. Back up the unchanged SQLite database

```bash
deploy_stamp=$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -o minimart -g minimart -m 750 /var/backups/minimart
sudo -u minimart sqlite3 /var/lib/minimart/minimart.db ".backup '/var/backups/minimart/pre-deploy-${deploy_stamp}.db'"
sudo -u minimart sqlite3 "/var/backups/minimart/pre-deploy-${deploy_stamp}.db" "PRAGMA quick_check;"
```

Expected database-check result: `ok`.

**Hard-to-undo point:** Do not continue after a failed backup check when the release changes the database schema.

### 7. Switch to the tested `main` commit

```bash
sudo -u minimart git switch main
sudo -u minimart git pull --ff-only origin main
sudo -u minimart git rev-parse HEAD
```

Compare the printed commit with the exact commit that passed GitHub Actions. `--ff-only` prevents an unplanned production merge.

### 8. Install the release dependencies

```bash
sudo -u minimart /opt/minimart/.venv/bin/python -m pip install --requirement /opt/minimart/requirements.txt
```

This uses the production virtual environment. A dependency downgrade or incompatible version can affect rollback, so requirements should be pinned and reviewed.

### 9. Handle the database deliberately

For the current schema, `minimart.db` is **preserved in place**. Do not delete it, copy a development database over it or run `git clean` against its directory.

If the release has no schema change, continue to Step 10. If it includes a schema change, run only the separately reviewed migration command recorded for that release.

**Hard-to-undo point:** A destructive or incompatible migration can make the previous application version unusable. A code rollback does not reverse a migration or restore overwritten data.

### 10. Start the production service

```bash
sudo systemctl start minimart
sudo systemctl status minimart --no-pager
```

systemd starts Gunicorn using `/etc/minimart/minimart.env`.

### 11. Verify the release

```bash
sudo systemctl is-active minimart
curl --fail --silent --show-error http://127.0.0.1:8000/ > /dev/null
curl --fail --silent --show-error http://127.0.0.1:8000/login > /dev/null
sudo -u minimart sqlite3 /var/lib/minimart/minimart.db "PRAGMA quick_check;"
sudo journalctl -u minimart --since "10 minutes ago" --no-pager
```

Expected results: service `active`, both HTTP commands return exit code 0, database result `ok`, and no repeated startup or database errors.

### 12. Observe for 30 minutes

Keep the Deployment Owner available for the first 30 minutes. Watch the two alert conditions in [monitoring.md](monitoring.md), verify one controlled checkout and confirm that users can authenticate and that an administrator can add a valid test product.

## Rollback trigger conditions

| Trigger | Measurable condition | Action |
|---|---|---|
| Application unavailable | **3 consecutive failed availability checks, one minute apart** | Begin the rollback decision immediately. |
| Order/database writes failing | **3 order-write errors within 10 minutes**, or **100% of checkout attempts fail when at least 3 attempts occurred** | Begin the rollback decision immediately. |

## Rollback decision rule

The **Deployment Owner** decides whether to roll back. If that person is unavailable, the nominated MiniMart team lead becomes the decision-maker.

The decision must be made within **5 minutes of an alert firing**. Roll back when the alert started during deployment or within the 30-minute observation period and the new release cannot be ruled out as the cause. If the cause remains uncertain after five minutes, rollback is the default.

Do not perform a code rollback when the release made a database schema change that is incompatible with the previous version. Keep MiniMart stopped and use a separately approved database-recovery procedure.

## Rollback commands

The example uses `v1.0` as the last known-good tag. Verify the real target before the maintenance window.

### 1. Resolve the target before stopping the service

```bash
cd /opt/minimart
sudo -u minimart git fetch --tags origin
sudo -u minimart git rev-parse --verify "v1.0^{commit}"
sudo -u minimart git status --short
```

Expected worktree result: no output. Stop if it is not clean.

### 2. Record the failed release

```bash
sudo -u minimart git rev-parse HEAD | sudo tee /var/lib/minimart/failed-release.txt > /dev/null
```

This preserves evidence and makes a later forward recovery possible.

### 3. Stop MiniMart

```bash
sudo systemctl stop minimart
```

### 4. Back up the database as it exists at incident time

```bash
rollback_stamp=$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -o minimart -g minimart -m 750 /var/backups/minimart
sudo -u minimart sqlite3 /var/lib/minimart/minimart.db ".backup '/var/backups/minimart/pre-rollback-${rollback_stamp}.db'"
sudo -u minimart sqlite3 "/var/backups/minimart/pre-rollback-${rollback_stamp}.db" "PRAGMA quick_check;"
```

Expected result: `ok`. This backup preserves the incident state; it does not repair it.

### 5. Switch application code to the known-good release

```bash
sudo -u minimart git switch --detach v1.0
```

### 6. Restore dependencies required by that release

```bash
sudo -u minimart /opt/minimart/.venv/bin/python -m pip install --requirement /opt/minimart/requirements.txt
```

### 7. Start MiniMart

```bash
sudo systemctl start minimart
sudo systemctl status minimart --no-pager
```

The rollback deliberately leaves `/etc/minimart/minimart.env` and `/var/lib/minimart/minimart.db` in place.

## Post-rollback verification

### Confirm the code version

```bash
cd /opt/minimart
test "$(git rev-parse HEAD)" = "$(git rev-list -n 1 v1.0)" && echo "Correct release is running"
```

### Confirm the service

```bash
sudo systemctl is-active minimart
```

Expected result: `active`.

### Repeat the availability check three times

```bash
for attempt in 1 2 3
do
    curl --fail --silent --show-error http://127.0.0.1:8000/ > /dev/null || exit 1
    echo "Availability check ${attempt} passed"
    [ "$attempt" -eq 3 ] || sleep 60
done
```

### Check database integrity

```bash
sudo -u minimart sqlite3 /var/lib/minimart/minimart.db "PRAGMA quick_check;"
```

Expected result: `ok`.

### Review post-rollback errors

```bash
sudo journalctl -u minimart --since "10 minutes ago" --no-pager
sudo tail -n 200 /opt/minimart/logs/app.log
```

Using the designated test account, place one controlled test order through the browser. Confirm an `order_placed` event rather than `order_write_error`.

Rollback is successful only when:

- The tag's exact commit is running.
- The systemd service is active.
- Three one-minute availability checks pass consecutively.
- SQLite reports `ok`.
- A controlled checkout succeeds.
- No new order-write failure occurs during the following 10 minutes.

## Known rollback limits

- Reverting code does **not** undo orders, users or products already written to `minimart.db`.
- It does not repair incorrect values written by the failed release.
- It does not restore deleted or overwritten rows.
- It does not reverse a schema migration. The previous code may be incompatible with the current schema.
- Restoring the pre-deployment database is not part of normal rollback. Doing so would discard every legitimate change made after the backup and requires separate approval.
- Rollback does not fix a full disk, SQLite corruption, filesystem permissions, persistent database locks or incorrect production environment variables.
- Requests in progress when the service stops may fail and must be retried.
- Sessions may be invalid if releases expect different session data or if `SECRET_KEY` changes.

## Rollback rehearsal

Do not approve this runbook until it has been rehearsed.

```bash
git tag v1.0
git push origin v1.0
```

Then:

1. Make a visible non-database change.
2. Commit, push and deploy it to the rehearsal environment.
3. Roll back using only this document.
4. Record every missing, incorrect or ambiguous step.
5. Correct the runbook.
6. Repeat until verification succeeds without improvisation.

Never rehearse database restoration against the only copy of production data.

