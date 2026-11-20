-- Extensions enabled for the canonical transport database (Phase 0.3).
-- The postgis/postgis image ships the PostGIS binaries; the extension must be
-- created explicitly in the target database. Phase 1 adds spatial types,
-- SRID constraints and indexes on top of this.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Dedicated integration-test database (I-18): integration tests migrate and
-- run against this DB so test cleanup never wipes development data.
SELECT 'CREATE DATABASE journey_planner_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'journey_planner_test')\gexec
