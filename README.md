    # MiniMart - Secure Checkpoint

    ## First run

    ```bash
    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    # Windows: copy .env.example .env
    # macOS/Linux: cp .env.example .env
    python app.py
    ```

    Replace the placeholder `SECRET_KEY` in `.env` with a private value before running.

    Demo accounts: `admin / admin123` and `shopper / password1`.

    Known limitations for the course exercise: there is no CSRF protection and no login rate limiting. These are documented in `docs/security-review.md`.

This activity begins before `git init`; no `.git` folder is included.
