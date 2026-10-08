import json
import secrets
from pathlib import Path


class NodeIdentity:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.node_id = self._load_or_create()

    def _load_or_create(self):
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            node_id = data.get("node_id")
            if isinstance(node_id, str) and len(node_id) == 64:
                return node_id
            raise ValueError("Invalid persisted P2P node identity.")
        node_id = secrets.token_hex(32)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"node_id": node_id}, sort_keys=True),
                encoding="utf-8",
            )
        return node_id
