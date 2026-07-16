import time
class ProofOfWork:

    @staticmethod
    def mine(block):

        target = "0" * block.difficulty

        while True:

            block.hash = block.calculate_hash()
            if block.nonce % 10000 == 0:
                print(
                    f"Mining... Nonce={block.nonce} Hash={block.hash[:12]}"
                )
            time.sleep(0.0001)  
            if block.hash.startswith(target):
                print(f"\n Block mined!")
                print(f"Nonce: {block.nonce}")
                print(f"Hash : {block.hash}\n")
                break

            block.nonce += 1

        return block