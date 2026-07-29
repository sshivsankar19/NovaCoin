from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction

chain = Blockchain()

miner = Wallet()

print("Before mining:")
print(chain.get_balance(miner.address))

chain.mine_pending_transactions(miner.address)

print()

print("After mining:")
print(chain.get_balance(miner.address))