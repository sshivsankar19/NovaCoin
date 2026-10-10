-- Persist the explicit PoW algorithm and protocol version for V2 blocks.
-- Existing V1 rows retain the SHA-256/V1 defaults.
ALTER TABLE blocks
    ADD COLUMN IF NOT EXISTS algorithm VARCHAR(50) NOT NULL
    DEFAULT 'SHA256_PROOF_OF_WORK';

ALTER TABLE blocks
    ADD COLUMN IF NOT EXISTS protocol_version INTEGER NOT NULL
    DEFAULT 1;
