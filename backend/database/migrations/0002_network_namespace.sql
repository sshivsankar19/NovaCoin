-- Namespace canonical Mainnet data without rewriting legacy rows.
ALTER TABLE blockchains
    ADD COLUMN IF NOT EXISTS network_id VARCHAR(128);

-- Legacy databases may have a symbol-only unique constraint. A symbol can
-- exist in both legacy/test data and the canonical Mainnet namespace.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'blockchains'::regclass
          AND conname = 'uq_blockchains_symbol'
    ) THEN
        ALTER TABLE blockchains DROP CONSTRAINT uq_blockchains_symbol;
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_blockchains_network_symbol
    ON blockchains (network_id, symbol)
    WHERE network_id IS NOT NULL;
