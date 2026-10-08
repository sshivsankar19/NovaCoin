import multiprocessing
import time

from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from p2p.peer_manager import PeerManager


def _node_a(queue, ready):
    chain = Blockchain(mainnet_consensus=True)
    manager = PeerManager(chain, port=0)
    manager.start()
    chain.mine_pending_transactions(Wallet().address)
    queue.put(("address", manager.port, chain.get_latest_block().hash))
    ready.wait(12)
    manager.stop()


def _node_b(queue, address):
    chain = Blockchain(mainnet_consensus=True)
    manager = PeerManager(chain, port=0)
    manager.start()
    manager.connect(address)
    deadline = time.time() + 10
    while time.time() < deadline and chain.get_latest_block().index == 0:
        time.sleep(0.05)
    queue.put(("result", chain.get_latest_block().hash, chain.get_latest_block().index))
    manager.stop()


def test_two_independent_processes_synchronize_over_tcp():
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    ready = context.Event()
    node_a = context.Process(target=_node_a, args=(queue, ready))
    node_a.start()
    kind, port, expected_hash = queue.get(timeout=20)
    assert kind == "address"
    node_b = context.Process(
        target=_node_b,
        args=(queue, ("127.0.0.1", port)),
    )
    node_b.start()
    result = queue.get(timeout=20)
    ready.set()
    node_b.join(timeout=10)
    node_a.join(timeout=10)
    assert result == ("result", expected_hash, 1)
    assert node_a.exitcode == 0
    assert node_b.exitcode == 0
