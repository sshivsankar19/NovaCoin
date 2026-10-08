from decimal import Decimal

import pytest

from blockchain.money import format_nvc, from_atomic_units, to_atomic_units
from blockchain.protocol import (
    GENESIS_HASH,
    HALVING_INTERVAL,
    INITIAL_BLOCK_REWARD_ATOMIC,
    get_block_subsidy,
)


def test_atomic_conversion_is_exact():
    assert to_atomic_units("1.00000001") == 100000001
    assert from_atomic_units(100000001) == Decimal("1.00000001")
    assert format_nvc(100000001) == "1.00000001"


def test_atomic_conversion_rejects_precision_loss():
    with pytest.raises(ValueError):
        to_atomic_units("0.000000001")


def test_subsidy_halves_deterministically():
    assert get_block_subsidy(0) == INITIAL_BLOCK_REWARD_ATOMIC
    assert get_block_subsidy(HALVING_INTERVAL) == INITIAL_BLOCK_REWARD_ATOMIC // 2
    assert get_block_subsidy(HALVING_INTERVAL * 2) == INITIAL_BLOCK_REWARD_ATOMIC // 4


def test_genesis_identity_is_fixed():
    assert len(GENESIS_HASH) == 64
    assert GENESIS_HASH == "4b2912db207f531097fd0ca8728405bb5350a4ff4b89d343893403fb4fcb0262"
