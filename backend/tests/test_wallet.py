from blockchain.wallet import Wallet


def test_wallet_generates_an_address_and_repr():
    wallet = Wallet()

    assert len(wallet.address) == 64
    assert wallet.address == wallet.address.lower()
    assert repr(wallet).startswith("Wallet(")
