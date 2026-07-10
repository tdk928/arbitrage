-- Local dev: role arbitrage / password arbitrage
-- Run as a superuser (e.g. your macOS Postgres user):
--   psql -d postgres -f sql/bootstrap/create_arbitrage_user.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'arbitrage') THEN
        CREATE ROLE arbitrage LOGIN PASSWORD 'arbitrage';
    ELSE
        ALTER ROLE arbitrage WITH LOGIN PASSWORD 'arbitrage';
    END IF;
END
$$;

SELECT 'CREATE DATABASE arbitrage OWNER arbitrage'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'arbitrage')\gexec

GRANT ALL PRIVILEGES ON DATABASE arbitrage TO arbitrage;

\connect arbitrage

GRANT ALL ON SCHEMA public TO arbitrage;
ALTER SCHEMA public OWNER TO arbitrage;

-- Reassign existing objects when re-running on a DB created by another user.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO arbitrage', r.tablename);
    END LOOP;
    FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO arbitrage', r.sequencename);
    END LOOP;
END $$;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO arbitrage;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO arbitrage;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO arbitrage;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO arbitrage;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO arbitrage;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO arbitrage;
