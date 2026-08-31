from blockchain.blockchain import Blockchain


def test_mining_pays_the_configured_reward():
    chain = Blockchain(difficulty=1)
    miner = "miner-address"

    assert chain.get_balance(miner) == 0
    chain.mine_pending_transactions(miner)

    assert len(chain.chain) == 2
    assert chain.get_balance(miner) == chain.mining_reward
