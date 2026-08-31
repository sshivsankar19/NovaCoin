from blockchain.transaction import Transaction


def test_transaction_has_id_and_readable_representation():
    transaction = Transaction("Alice", "Bob", 25)

    assert len(transaction.txid) == 64
    assert transaction.sender == "Alice"
    assert transaction.receiver == "Bob"
    assert "Alice" in repr(transaction)
