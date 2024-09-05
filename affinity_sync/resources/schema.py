SCHEMA = '''
CREATE SCHEMA IF NOT EXISTS affinity;

DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'synctype') THEN
       CREATE TYPE affinity.SyncType AS ENUM ('person', 'company', 'list', 'view');
   END IF;
END $$;


CREATE TABLE IF NOT EXISTS affinity.api_call_entitlement 
(
    id              SERIAL PRIMARY KEY,
    user_limit      INT NOT NULL,
    user_remaining  INT NOT NULL,
    user_reset      INT NOT NULL,
    org_limit       INT NOT NULL,
    org_remaining   INT NOT NULL,
    org_reset       INT NOT NULL,
    inserted_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS affinity.sync
(
    id                SERIAL PRIMARY KEY,
    type              affinity.SyncType NOT NULL,
    frequency_minutes INT NOT NULL,
    data              JSONB,
    live              BOOLEAN NOT NULL,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (type, data)
);

CREATE TABLE IF NOT EXISTS affinity.sync_log
(
    id         SERIAL PRIMARY KEY,
    sync_id    INT REFERENCES affinity.sync (id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);


CREATE TABLE IF NOT EXISTS affinity.person_field
(
    id                SERIAL PRIMARY KEY,
    affinity_id       TEXT                                NOT NULL,
    name              TEXT,
    type              TEXT,
    enrichment_source TEXT,
    value_type        TEXT,
    valid_from        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to          TIMESTAMP,
    UNIQUE (affinity_id, valid_from),
    UNIQUE (affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_person_field_affinity_id_valid_to_valid_from
    ON affinity.person_field (affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.person
(
    id                    SERIAL PRIMARY KEY,
    affinity_id           INT                                 NOT NULL,
    first_name            TEXT,
    last_name             TEXT,
    primary_email_address TEXT,
    email_addresses       TEXT[],
    type                  TEXT,
    fields                JSONB,
    valid_from            TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to              TIMESTAMP,
    UNIQUE (affinity_id, valid_from),
    UNIQUE (affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_person_affinity_id_valid_to_valid_from
    ON affinity.person (affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.company_field
(
    id                SERIAL PRIMARY KEY,
    affinity_id       TEXT                                NOT NULL,
    name              TEXT,
    type              TEXT,
    enrichment_source TEXT,
    value_type        TEXT,
    valid_from        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to          TIMESTAMP,
    UNIQUE (affinity_id, valid_from),
    UNIQUE (affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_company_field_affinity_id_valid_to_valid_from
    ON affinity.company_field (affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.company
(
    id          SERIAL PRIMARY KEY,
    affinity_id INT                                 NOT NULL,
    name        TEXT,
    domain      TEXT,
    domains     TEXT[],
    is_global   BOOLEAN,
    fields      JSONB,
    valid_from  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to    TIMESTAMP,
    UNIQUE (affinity_id, valid_from),
    UNIQUE (affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_company_affinity_id_valid_to_valid_from
    ON affinity.company (affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.list_metadata
(
    id          SERIAL PRIMARY KEY,
    affinity_id INT                                 NOT NULL,
    name        TEXT,
    creator_id  INT,
    owner_id    INT,
    is_public   BOOLEAN,
    type        TEXT,
    valid_from  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to    TIMESTAMP,
    UNIQUE (affinity_id, valid_from),
    UNIQUE (affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_list_metadata_affinity_id_valid_to_valid_from
    ON affinity.list_metadata (affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.list_field
(
    id                SERIAL PRIMARY KEY,
    list_affinity_id  INT                                 NOT NULL,
    affinity_id       TEXT                                NOT NULL,
    name              TEXT,
    type              TEXT,
    enrichment_source TEXT,
    value_type        TEXT,
    valid_from        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to          TIMESTAMP,
    UNIQUE (list_affinity_id, affinity_id, valid_from),
    UNIQUE (list_affinity_id, affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_list_field_affinity_id_valid_to_valid_from
    ON affinity.list_field (list_affinity_id, affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.list_entry
(
    id               SERIAL PRIMARY KEY,
    list_affinity_id INT                                 NOT NULL,
    affinity_id      INT                                 NOT NULL,
    type             TEXT,
    created_at       TIMESTAMP,
    creator_id       INT,
    entity           JSONB,
    valid_from       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to         TIMESTAMP,
    UNIQUE (list_affinity_id, affinity_id, valid_from),
    UNIQUE (list_affinity_id, affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_list_entry_list_affinity_id_affinity_id_valid_to_valid_from
    ON affinity.list_entry (list_affinity_id, affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.view_metadata
(
    id               SERIAL PRIMARY KEY,
    list_affinity_id INT                                 NOT NULL,
    affinity_id      INT                                 NOT NULL,
    name             TEXT,
    type             TEXT,
    created_at       TIMESTAMP,
    valid_from       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to         TIMESTAMP,
    UNIQUE (list_affinity_id, affinity_id, valid_from),
    UNIQUE (list_affinity_id, affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_view_metadata
    ON affinity.view_metadata (list_affinity_id, affinity_id, valid_to, valid_from);


CREATE TABLE IF NOT EXISTS affinity.view_entry
(
    id               SERIAL PRIMARY KEY,
    list_affinity_id INT                                 NOT NULL,
    view_affinity_id INT                                 NOT NULL,
    affinity_id      INT                                 NOT NULL,
    type             TEXT,
    created_at       TIMESTAMP,
    creator_id       INT,
    entity           JSONB,
    valid_from       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to         TIMESTAMP,
    UNIQUE (list_affinity_id, view_affinity_id, affinity_id, valid_from),
    UNIQUE (list_affinity_id, view_affinity_id, affinity_id, valid_to)
);
CREATE INDEX IF NOT EXISTS idx_view_entry_view_affinity_id_affinity_id_valid_to_valid_from
    ON affinity.view_entry (list_affinity_id, view_affinity_id, affinity_id, valid_to, valid_from);
'''
