import time

from p2p.private_testnet import PrivateTestnet


def test_bounded_five_node_long_run_converges():
    testnet = PrivateTestnet(5)
    started = time.monotonic()
    blocks_mined = 0
    restarts = 0
    try:
        testnet.start()
        assert testnet.connect(1, 0)
        assert testnet.connect(2, 0)
        assert testnet.connect(3, 0)
        assert testnet.connect(4, 0)
        for index in range(50):
            node = index % 5
            testnet.mine_fast(node)
            blocks_mined += 1
            converged = testnet.wait_for_convergence(timeout=60)
            assert converged is not None
            if index in {12, 27, 41}:
                restarted_node = (node + 1) % 5
                testnet.restart(restarted_node)
                restarts += 1
                assert testnet.connect(restarted_node, 0)
        statuses = [testnet.status(index) for index in range(5)]
        assert len({status["tip"] for status in statuses}) == 1
        assert len({status["height"] for status in statuses}) == 1
        assert len({status["chain_work"] for status in statuses}) == 1
        assert blocks_mined == 50
        assert restarts == 3
        assert time.monotonic() - started < 300
    finally:
        testnet.stop()
