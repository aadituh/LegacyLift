-- Project data from legacylift.models: one project, its source files, and its runs.
-- NeonProjectStore applies this file on startup when DATABASE_URL is set.

CREATE TABLE IF NOT EXISTS projects (
    id text PRIMARY KEY,
    name text NOT NULL,
    created_at timestamptz NOT NULL,
    files_added integer NOT NULL
);

CREATE TABLE IF NOT EXISTS source_files (
    project_id text NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    id text NOT NULL,
    name text NOT NULL,
    kind text NOT NULL,
    content text NOT NULL,
    position integer NOT NULL,
    PRIMARY KEY (project_id, id)
);

CREATE TABLE IF NOT EXISTS runs (
    project_id text NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    id text NOT NULL,
    kind text NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL,
    position integer NOT NULL,
    PRIMARY KEY (project_id, id)
);

CREATE TABLE IF NOT EXISTS converted_files (
    project_id text NOT NULL,
    run_id text NOT NULL,
    position integer NOT NULL,
    source_file_id text NOT NULL,
    source_name text NOT NULL,
    python_name text NOT NULL,
    program_name text NOT NULL,
    python text NOT NULL,
    notes jsonb NOT NULL,
    status text NOT NULL,
    PRIMARY KEY (project_id, run_id, position),
    FOREIGN KEY (project_id, run_id) REFERENCES runs (project_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_id_counter (
    singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    last_number integer NOT NULL
);
