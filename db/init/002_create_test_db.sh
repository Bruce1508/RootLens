#!/bin/sh
# Creates a second database (rootlens_test) for the test suite, owned by
# the same rootlens_app role, with rootlens_readonly granted access on it
# too. Runs once, automatically, alongside 001_create_roles.sh.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE rootlens_test OWNER ${POSTGRES_USER};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname rootlens_test <<-EOSQL
    GRANT CONNECT ON DATABASE rootlens_test TO rootlens_readonly;
    GRANT USAGE ON SCHEMA public TO rootlens_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO rootlens_readonly;
EOSQL
