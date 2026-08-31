from blockchain.wallet import Wallet


def test_wallet_signature_verifies_only_for_original_message():
    wallet = Wallet()
    message = "Send 25000 coins to Bob"

    signature = wallet.sign(message)

    assert len(signature) > 0
    assert wallet.verify(message, signature) is True
    assert wallet.verify("tampered", signature) is False
