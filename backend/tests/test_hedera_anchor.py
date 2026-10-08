import pytest

from web3.hedera_anchor import get_anchor_configuration, validate_anchor


def test_validate_anchor_preserves_hash_as_bytes32():
    index, block_hash = validate_anchor(2, "AB" * 32)

    assert index == 2
    assert block_hash == f"0x{'ab' * 32}"


@pytest.mark.parametrize(
    "index, block_hash",
    [
        (0, "11" * 32),
        (-1, "11" * 32),
        (1, "11" * 31),
        (1, "zz" * 32),
    ],
)
def test_validate_anchor_rejects_invalid_values(index, block_hash):
    with pytest.raises(ValueError):
        validate_anchor(index, block_hash)


def test_configuration_exposes_testnet_defaults_without_private_key(monkeypatch):
    monkeypatch.delenv("HEDERA_PRIVATE_KEY", raising=False)
    configuration = get_anchor_configuration()

    assert configuration["network"] == "testnet"
    assert configuration["chain_id"] == 296
    assert "private" not in configuration
