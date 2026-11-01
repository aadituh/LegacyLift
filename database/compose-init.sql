-- Docker Compose only: runs once when the db-data volume is created.
-- Neon Auth creates neon_auth."user" on Neon; this stand-in lets database/schema.sql
-- (projects.owner_id references it) apply to the local Postgres container.
CREATE SCHEMA IF NOT EXISTS neon_auth;
CREATE TABLE IF NOT EXISTS neon_auth."user" (id uuid PRIMARY KEY);
