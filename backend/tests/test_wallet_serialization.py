from blockchain.wallet import Wallet


def test_wallet_round_trip_preserves_keys_and_address():
    wallet = Wallet()
    restored = Wallet.from_dict(wallet.to_dict())

    assert restored.address == wallet.address
    signature = restored.sign("round trip")
    assert restored.verify("round trip", signature) is True
