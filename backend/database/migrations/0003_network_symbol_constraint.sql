-- Remove the legacy symbol-only uniqueness constraint so the same symbol can
-- exist in separate legacy and canonical network namespaces.
ALTER TABLE blockchains
    DROP CONSTRAINT IF EXISTS blockchains_symbol_key;

ALTER TABLE blockchains
    DROP CONSTRAINT IF EXISTS uq_blockchains_symbol;

CREATE UNIQUE INDEX IF NOT EXISTS uq_blockchains_network_symbol
    ON blockchains (network_id, symbol)
    WHERE network_id IS NOT NULL;
