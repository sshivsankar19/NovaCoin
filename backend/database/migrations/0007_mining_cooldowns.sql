
CREATE TABLE IF NOT EXISTS mining_cooldowns (
    wallet_address VARCHAR(128) PRIMARY KEY,
    last_mined_at TIMESTAMPTZ NOT NULL
);
