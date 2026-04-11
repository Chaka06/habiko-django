import os


def pytest_configure(config):
    """Set required env vars before Django settings are loaded by pytest-django."""
    os.environ.setdefault("DEBUG", "True")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
    os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
    # Use SQLite for tests — no external Postgres required
    os.environ.setdefault("DB_ENGINE", "sqlite")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")


# Pytest collection configuration to ignore Django management commands named like tests
collect_ignore_glob = [
    "*/management/commands/test_*.py",
]
