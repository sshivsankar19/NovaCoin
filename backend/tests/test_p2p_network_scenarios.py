from p2p.private_testnet import PrivateTestnet


def test_five_node_multi_hop_convergence():
    testnet = PrivateTestnet(5)
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        assert testnet.connect(2, 1)
        assert testnet.connect(3, 2)
        assert testnet.connect(4, 3)
        expected = testnet.mine(0)
        statuses = testnet.wait_for_convergence(timeout=60)
        assert statuses is not None
        assert all(status["tip"] == expected for status in statuses)
        assert len({status["chain_work"] for status in statuses}) == 1
    finally:
        testnet.stop()


def test_partition_reconnect_converges_to_valid_chain():
    testnet = PrivateTestnet(5)
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        assert testnet.connect(2, 1)
        assert testnet.connect(3, 2)
        assert testnet.connect(4, 3)
        bridge_id = testnet.status(2)["node_id"]
        assert testnet.disconnect(1, bridge_id)
        testnet.disconnect(2, testnet.status(1)["node_id"])
        left_tip = testnet.mine(0)
        right_tip = testnet.mine(2)
        assert left_tip != right_tip
        assert testnet.connect(1, 2)
        testnet.connect(2, 1)
        statuses = testnet.wait_for_convergence(timeout=60)
        assert statuses is not None
        assert len({status["tip"] for status in statuses}) == 1
        assert all(status["chain_work"] > 0 for status in statuses)
    finally:
        testnet.stop()


def test_restart_recovers_persisted_canonical_state():
    testnet = PrivateTestnet(3)
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        expected = testnet.mine(0)
        assert testnet.wait_for_node_height(1, 1, timeout=40)
        restarted_port = testnet.restart(1)
        assert restarted_port > 0
        restarted = testnet.status(1)
        assert restarted["tip"] == expected
        assert restarted["height"] == 1
        assert restarted["chain_work"] == 33_554_432
    finally:
        testnet.stop()


def test_restart_after_reorganization_converges():
    testnet = PrivateTestnet(5)
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        assert testnet.connect(2, 1)
        assert testnet.connect(3, 2)
        assert testnet.connect(4, 3)
        bridge_id = testnet.status(2)["node_id"]
        testnet.disconnect(1, bridge_id)
        testnet.disconnect(2, testnet.status(1)["node_id"])
        assert testnet.mine_fast(0)
        assert testnet.mine_fast(2)
        assert testnet.connect(1, 2)
        testnet.connect(2, 1)
        assert testnet.wait_for_convergence(timeout=60) is not None
        restarted_node = 4
        testnet.restart(restarted_node)
        assert testnet.connect(restarted_node, 0)
        statuses = testnet.wait_for_convergence(timeout=60)
        assert statuses is not None
        assert len({status["tip"] for status in statuses}) == 1
        assert len({status["chain_work"] for status in statuses}) == 1
    finally:
        testnet.stop()
