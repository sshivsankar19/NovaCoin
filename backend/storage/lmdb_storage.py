import lmdb

from storage.storage_engine import StorageEngine


class LMDBStorage(StorageEngine):
    """LMDB implementation of the StorageEngine interface."""

    def __init__(self, db_path: str = "database/lmdb"):
        self.env = lmdb.open(
            db_path,
            create=True,
            map_size=100 * 1024 * 1024,  # 100 MB
        )

    def put(self, key: str, value: bytes) -> None:
        with self.env.begin(write=True) as txn:
            txn.put(key.encode("utf-8"), value)

    def get(self, key: str) -> bytes | None:
        with self.env.begin() as txn:
            return txn.get(key.encode("utf-8"))

    def delete(self, key: str) -> None:
        with self.env.begin(write=True) as txn:
            txn.delete(key.encode("utf-8"))

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def iterate(self, prefix: str = ""):
        prefix_bytes = prefix.encode("utf-8")

        with self.env.begin() as txn:
            cursor = txn.cursor()

            for key, value in cursor:
                if key.startswith(prefix_bytes):
                    yield (
                        key.decode("utf-8"),
                        value,
                    )

    def close(self) -> None:
        self.env.close()