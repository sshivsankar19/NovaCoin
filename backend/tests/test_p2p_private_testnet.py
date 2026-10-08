from p2p.private_testnet import PrivateTestnet


def test_three_node_private_testnet_converges_over_multiple_hops():
    testnet = PrivateTestnet(3)
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        assert testnet.connect(2, 1)
        expected_hash = testnet.mine(0)
        assert testnet.wait_for_height(1)
        statuses = [testnet.status(index) for index in range(3)]
        assert all(status["tip"] == expected_hash for status in statuses)
        assert all(status["network_id"] == "novacoin-mainnet-v1"
                   for status in statuses)
    finally:
        testnet.stop()
