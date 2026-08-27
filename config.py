"""Environment-based configuration for MiniMart."""

import os

from dotenv import load_dotenv


def load_config():
    load_dotenv()
    secret_key = os.environ.get("SECRET_KEY")
    database_path = os.environ.get("DATABASE_PATH")
    if not secret_key:
        raise RuntimeError("SECRET_KEY is required. Copy .env.example to .env and set a private value.")
    if not database_path:
        raise RuntimeError("DATABASE_PATH is required. Copy .env.example to .env and set a database path.")
    return {
        "SECRET_KEY": secret_key,
        "DATABASE": database_path,
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO").upper(),
        "LOG_FILE": os.environ.get("LOG_FILE", "logs/app.log"),
    }
