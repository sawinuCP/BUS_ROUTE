-- Extensions enabled for the canonical transport database (Phase 0.3).
-- The postgis/postgis image ships the PostGIS binaries; the extension must be
-- created explicitly in the target database. Phase 1 adds spatial types,
-- SRID constraints and indexes on top of this.

CREATE EXTENSION IF NOT EXISTS postgis;
