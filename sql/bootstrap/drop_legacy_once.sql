-- ONE-TIME bootstrap: drop legacy objects from old branches.
-- NOT part of Flyway migrations. Run manually before first migrate on an existing DB:
--   psql $DATABASE_URL -f sql/bootstrap/drop_legacy_once.sql

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
