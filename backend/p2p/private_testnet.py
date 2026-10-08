"""Small isolated multi-process harness for private P2P testing."""

import multiprocessing
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from p2p.peer_manager import PeerManager
from blockchain.proof_of_work import ProofOfWork


def _node_process(command_queue, result_queue, state_dir):
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = "sqlite:///" + str(
        Path(state_dir) / "node.sqlite"
    )
    from flask import Flask
    from database.block_persistence import BlockPersistence
    from database.blockchain_loader import initialize_blockchain
    from database.postgres import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        chain = Blockchain(
            mainnet_consensus=True,
            block_persister=BlockPersistence.save,
        )
        initialize_blockchain(chain)
        manager = PeerManager(
            chain,
            port=0,
            identity_path=str(Path(state_dir) / "node.json"),
            max_peers=16,
            max_inbound_peers=16,
            max_outbound_peers=16,
            context_factory=app.app_context,
        )
        manager.start()
        result_queue.put(("started", manager.port))
        while True:
            command = command_queue.get()
            action = command[0]
            if action == "connect":
                result_queue.put(("connect", manager.connect(command[1])))
            elif action == "mine":
                wallet = Wallet()
                chain.mine_pending_transactions(wallet.address)
                manager.broadcast_block(chain.get_latest_block())
                result_queue.put(("mine", chain.get_latest_block().hash))
            elif action == "mine_fast":
                wallet = Wallet()
                block = chain.build_pending_block(wallet.address)
                previous_time = datetime.fromisoformat(
                    chain.get_latest_block().timestamp
                )
                block.timestamp = (
                    previous_time + timedelta(seconds=30)
                ).astimezone(timezone.utc).isoformat()
                block.hash = block.calculate_hash()
                ProofOfWork.mine(block)
                if not chain.accept_block(block):
                    raise RuntimeError("Testnet fast-mined block was rejected.")
                manager.broadcast_block(block)
                result_queue.put(("mine_fast", block.hash))
            elif action == "status":
                result_queue.put(("status", manager.status()))
            elif action == "disconnect":
                result_queue.put(("disconnect", manager.disconnect(command[1])))
            elif action == "restart":
                manager.stop()
                chain = Blockchain(
                    mainnet_consensus=True,
                    block_persister=BlockPersistence.save,
                )
                initialize_blockchain(chain)
                manager = PeerManager(
                    chain,
                    port=0,
                    identity_path=str(Path(state_dir) / "node.json"),
                    max_peers=16,
                    max_inbound_peers=16,
                    max_outbound_peers=16,
                    context_factory=app.app_context,
                )
                manager.start()
                result_queue.put(("restarted", manager.port))
            elif action == "stop":
                manager.stop()
                result_queue.put(("stopped", True))
                return


class PrivateTestnet:
    """Start independent local node processes without shared persistence."""

    def __init__(self, node_count=3):
        if node_count < 3:
            raise ValueError("Private testnet requires at least three nodes.")
        self.context = multiprocessing.get_context("spawn")
        self.root = Path(tempfile.mkdtemp(prefix="novacoin-testnet-"))
        self.commands = []
        self.results = []
        self.processes = []
        self.ports = []
        for index in range(node_count):
            command_queue = self.context.Queue()
            result_queue = self.context.Queue()
            process = self.context.Process(
                target=_node_process,
                args=(
                    command_queue,
                    result_queue,
                    str(self.root / ("node-" + str(index))),
                ),
            )
            self.commands.append(command_queue)
            self.results.append(result_queue)
            self.processes.append(process)

    def start(self):
        for process, result_queue in zip(self.processes, self.results):
            process.start()
            kind, port = result_queue.get(timeout=15)
            if kind != "started":
                raise RuntimeError("Private testnet node failed to start.")
            self.ports.append(port)

    def connect(self, node_index, target_index):
        self.commands[node_index].put(
            ("connect", ("127.0.0.1", self.ports[target_index]))
        )
        connected = self.results[node_index].get(timeout=10)[1]
        if not connected:
            return False
        source_node_id = self.status(node_index)["node_id"]
        deadline = time.time() + 10
        while time.time() < deadline:
            source_status = self.status(node_index)
            target_status = self.status(target_index)
            source_peers = source_status.get("peers", {})
            target_peers = target_status.get("peers", {})
            if (
                target_status["node_id"] in source_peers
                and source_node_id in target_peers
            ):
                return True
            time.sleep(0.05)
        return False

    def mine(self, node_index):
        self.commands[node_index].put(("mine",))
        return self.results[node_index].get(timeout=30)[1]

    def mine_fast(self, node_index):
        self.commands[node_index].put(("mine_fast",))
        return self.results[node_index].get(timeout=30)[1]

    def status(self, node_index):
        self.commands[node_index].put(("status",))
        return self.results[node_index].get(timeout=10)[1]

    def restart(self, node_index):
        self.commands[node_index].put(("restart",))
        port = self.results[node_index].get(timeout=15)[1]
        self.ports[node_index] = port
        return port

    def disconnect(self, node_index, peer_node_id):
        self.commands[node_index].put(("disconnect", peer_node_id))
        return self.results[node_index].get(timeout=10)[1]

    def wait_for_height(self, height, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if all(self.status(index)["height"] >= height
                   for index in range(len(self.processes))):
                return True
            time.sleep(0.1)
        return False

    def wait_for_node_height(self, node_index, height, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.status(node_index)["height"] >= height:
                return True
            time.sleep(0.1)
        return False

    def wait_for_convergence(self, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            statuses = [
                self.status(index)
                for index in range(len(self.processes))
            ]
            if (
                len({status["tip"] for status in statuses}) == 1
                and len({status["height"] for status in statuses}) == 1
                and len({status["chain_work"] for status in statuses}) == 1
            ):
                return statuses
            time.sleep(0.1)
        return None

    def stop(self):
        for command_queue in self.commands:
            command_queue.put(("stop",))
        for result_queue in self.results:
            result_queue.get(timeout=10)
        for process in self.processes:
            process.join(timeout=10)
        for process in self.processes:
            if process.is_alive():
                process.terminate()
