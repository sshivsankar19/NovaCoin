from database.models.blockchain_model import BlockchainModel


class BlockchainMapper:

    @staticmethod
    def to_model(blockchain):
        return BlockchainModel(
            name=blockchain.name,
            symbol=blockchain.symbol,
            network_id=getattr(blockchain, "network_id", None),
            algorithm=blockchain.algorithm,
            difficulty=blockchain.difficulty,
            block_reward=blockchain.mining_reward,
            block_time=getattr(blockchain, "block_time", None),
            is_active=True
        )

    @staticmethod
    def to_domain(model):
        return {
            "id": model.id,
            "name": model.name,
            "symbol": model.symbol,
            "algorithm": model.algorithm,
            "difficulty": model.difficulty,
            "block_reward": model.block_reward,
            "block_time": model.block_time,
            "is_active": model.is_active,
            "created_at": model.created_at
        }