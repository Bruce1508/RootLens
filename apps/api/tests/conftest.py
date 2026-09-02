import os

# Required Settings fields need a value for any test that imports app.main
# (module-level `Settings()` instantiation). Individual tests can still
# override via monkeypatch; this just guarantees collection never fails.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://rootlens_app:test@localhost:5432/rootlens_test"
)
os.environ.setdefault(
    "DATABASE_URL_READONLY",
    "postgresql+psycopg://rootlens_readonly:test@localhost:5432/rootlens_test",
)
