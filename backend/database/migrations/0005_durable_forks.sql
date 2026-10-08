-- Allow Mainnet fork blocks at the same height and persist canonical state.
-- Legacy rows and blocks are not rewritten.
ALTER TABLE blocks
    DROP CONSTRAINT IF EXISTS uq_blockchain_height;

DROP INDEX IF EXISTS uq_blockchain_height;

ALTER TABLE blockchains
    ADD COLUMN IF NOT EXISTS canonical_tip_hash VARCHAR(64);

ALTER TABLE blockchains
    ADD COLUMN IF NOT EXISTS canonical_height INTEGER;

ALTER TABLE blockchains
    ADD COLUMN IF NOT EXISTS canonical_work NUMERIC(78, 0);
