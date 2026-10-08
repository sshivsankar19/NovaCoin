import json
import uuid

PROTOCOL = "novacoin-p2p"
VERSION = 1
MAX_MESSAGE_BYTES = 1_000_000
MAX_BLOCKS_PER_MESSAGE = 128
MAX_TRANSACTIONS_PER_MESSAGE = 128
MAX_HEADERS_PER_MESSAGE = 128
MAX_LOCATOR_SIZE = 32
MAX_TRANSACTION_BYTES = 128_000
MAX_BLOCK_BYTES = 512_000

MESSAGE_TYPES = {
    "HANDSHAKE",
    "HANDSHAKE_ACK",
    "GET_STATUS",
    "STATUS",
    "GET_BLOCKS",
    "BLOCKS",
    "GET_HEADERS",
    "HEADERS",
    "TX",
    "TX_ACK",
    "BLOCK",
    "BLOCK_ACK",
    "PING",
    "PONG",
    "GOODBYE",
}


def make_message(network_id, message_type, payload=None, request_id=None):
    if message_type not in MESSAGE_TYPES:
        raise ValueError("Unsupported P2P message type.")
    return {
        "protocol": PROTOCOL,
        "version": VERSION,
        "network_id": network_id,
        "type": message_type,
        "request_id": request_id or uuid.uuid4().hex,
        "payload": payload or {},
    }


def encode(message):
    raw = json.dumps(
        message,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("P2P message is too large.")
    return raw + b"\n"


def decode(raw, network_id):
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("P2P message is too large.")
    try:
        message = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed P2P JSON.") from error
    if not isinstance(message, dict):
        raise ValueError("P2P message must be an object.")
    required = {"protocol", "version", "network_id", "type", "request_id", "payload"}
    if set(message) != required:
        raise ValueError("Invalid P2P message envelope.")
    if message["protocol"] != PROTOCOL or message["version"] != VERSION:
        raise ValueError("Unsupported P2P protocol.")
    if message["network_id"] != network_id:
        raise ValueError("Wrong P2P network.")
    if message["type"] not in MESSAGE_TYPES:
        raise ValueError("Unsupported P2P message type.")
    if not isinstance(message["request_id"], str) or len(message["request_id"]) > 100:
        raise ValueError("Invalid P2P request ID.")
    if not isinstance(message["payload"], dict):
        raise ValueError("Invalid P2P payload.")
    return message
