from abc import ABC, abstractmethod


class StorageEngine(ABC):
    """Abstract base class for key-value storage engines."""

    @abstractmethod
    def put(self, key: str, value: bytes) -> None:
        """Store a key-value pair."""
        pass

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        """Retrieve a value by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key-value pair."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check whether a key exists."""
        pass

    @abstractmethod
    def iterate(self, prefix: str = ""):
        """Iterate over key-value pairs with an optional prefix."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the storage engine."""
        pass