#!/bin/sh
# Creates the read-only Postgres role (ADR-0004). Runs once, automatically,
# on first container boot via /docker-entrypoint-initdb.d/ (shell scripts
# in that directory get direct access to the POSTGRES_* env vars; plain
# .sql files do not, hence a shell wrapper here instead of a bare .sql
# file). POSTGRES_USER/POSTGRES_DB/POSTGRES_PASSWORD (the owner role used
# by the container itself, i.e. rootlens_app) are provisioned by the
# official postgres image before this script runs.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE rootlens_readonly WITH LOGIN PASSWORD '${ROOTLENS_READONLY_PASSWORD}';

    -- Grant SELECT on tables created by future migrations too, not just
    -- tables that exist at init time.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO rootlens_readonly;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO rootlens_readonly;
    GRANT USAGE ON SCHEMA public TO rootlens_readonly;
EOSQL
