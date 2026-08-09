#!/usr/bin/env bash

set -Eeuo pipefail

required_variables=(
    POSTGRES_USER
    CUSTOMER_DB_NAME
    CUSTOMER_DB_USER
    CUSTOMER_DB_PASSWORD
    KEYCLOAK_DB_NAME
    KEYCLOAK_DB_USER
    KEYCLOAK_DB_PASSWORD
)

for variable_name in "${required_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
        printf 'Required initialization variable %s is not set.\n' "$variable_name" >&2
        exit 1
    fi
done

psql \
    --set=ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname postgres \
    --set=customer_db_name="$CUSTOMER_DB_NAME" \
    --set=customer_db_user="$CUSTOMER_DB_USER" \
    --set=customer_db_password="$CUSTOMER_DB_PASSWORD" \
    --set=keycloak_db_name="$KEYCLOAK_DB_NAME" \
    --set=keycloak_db_user="$KEYCLOAK_DB_USER" \
    --set=keycloak_db_password="$KEYCLOAK_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'customer_db_user', :'customer_db_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'customer_db_user') \gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'keycloak_db_user', :'keycloak_db_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'keycloak_db_user') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'customer_db_name', :'customer_db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'customer_db_name') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'keycloak_db_name', :'keycloak_db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'keycloak_db_name') \gexec

SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'customer_db_name') \gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO %I', :'customer_db_name', :'customer_db_user') \gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'keycloak_db_name') \gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO %I', :'keycloak_db_name', :'keycloak_db_user') \gexec
SQL
