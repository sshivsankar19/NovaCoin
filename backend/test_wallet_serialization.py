from blockchain.wallet import Wallet

wallet = Wallet()

data = wallet.to_dict()

copy = Wallet.from_dict(data)

print(wallet.address)
print(copy.address)

print()

print(wallet.address == copy.address)