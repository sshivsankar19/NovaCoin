from blockchain.wallet import Wallet

wallet = Wallet()

#message = "Send 25 coins to Bob"
message = "Send 25000 coins to Bob"

signature = wallet.sign(message)

print("Message:")
print(message)

print()

print("Signature:")
print(signature.hex())

print()

print(
    "Verified:",
    wallet.verify(message, signature)
)