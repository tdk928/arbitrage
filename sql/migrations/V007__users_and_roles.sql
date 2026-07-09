-- Application users and roles (anonymous is frontend-only, not stored here).

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

INSERT INTO roles (slug, name) VALUES
    ('client', 'Client'),
    ('admin', 'Admin');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active_from TIMESTAMPTZ,
    active_to TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role_id ON users (role_id);
