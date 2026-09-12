"""Flask API exposing HAWK key generation, signing, and verification.

This is a teaching demo for a post-quantum cryptography course. HAWK is broken
(see docs/security-status.md) and this server keeps private keys in plaintext in
process memory, so it must never be exposed beyond localhost.
"""

import base64
import binascii
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from hawk_crypto import hawkkeygen, hawksign, hawkverify

WEB_DIR = Path(__file__).resolve().parent / "web"

# logn -> HAWK-n. Only the three parameter sets in the v1.1 specification exist.
SUPPORTED_LOGN = (8, 9, 10)

# Signing cost is linear in message length and this server is single-threaded.
MAX_MESSAGE_BYTES = 4096

app = Flask(__name__, static_folder=None)
CORS(app)

# client_id -> {'logn': int, 'priv': np.uint8[], 'pub': np.uint8[]}
key_store = {}


def b64enc(arr):
    return base64.b64encode(arr.tobytes()).decode()


def b64dec(s):
    """Decode base64 into a uint8 array, rejecting malformed input."""
    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid base64: {exc}") from exc
    return np.frombuffer(raw, dtype=np.uint8)


def parse_logn(data, field="logn"):
    """Read and validate a logn parameter, defaulting to HAWK-512."""
    try:
        logn = int(data.get(field, 9))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer") from None
    if logn not in SUPPORTED_LOGN:
        raise ValueError(f"{field} must be one of {SUPPORTED_LOGN} (Hawk-256/512/1024)")
    return logn


def parse_message(data):
    """Read and validate the message field, returning it as bytes and uint8s."""
    message = data.get("message", "")
    if not isinstance(message, str):
        raise ValueError("message must be a string")
    raw = message.encode("utf-8")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError(f"message must be at most {MAX_MESSAGE_BYTES} bytes")
    return message, np.frombuffer(raw, dtype=np.uint8)


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "demo.html")


@app.route("/<path:filename>")
def web_asset(filename):
    return send_from_directory(WEB_DIR, filename)


@app.route("/api/keygen", methods=["POST"])
def api_keygen():
    data = request.get_json(force=True, silent=True) or {}
    client_id = str(data.get("client_id", "default"))
    try:
        logn = parse_logn(data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    priv, pub = hawkkeygen(logn)
    key_store[client_id] = {"logn": logn, "priv": priv, "pub": pub}
    return jsonify(
        client_id=client_id,
        logn=logn,
        variant=f"Hawk-{1 << logn}",
        pub_b64=b64enc(pub),
        priv_len=len(priv),
        pub_len=len(pub),
        message="Key pair generated successfully",
    )


@app.route("/api/sign", methods=["POST"])
def api_sign():
    data = request.get_json(force=True, silent=True) or {}
    client_id = str(data.get("client_id", "default"))
    if client_id not in key_store:
        return jsonify(error=f'No keys for client "{client_id}". Generate keys first.'), 400
    try:
        message, msg_bytes = parse_message(data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    ks = key_store[client_id]
    sig = hawksign(ks["logn"], ks["priv"], msg_bytes)
    return jsonify(
        client_id=client_id,
        logn=ks["logn"],
        variant=f'Hawk-{1 << ks["logn"]}',
        message=message,
        signature_b64=b64enc(sig),
        sig_len=len(sig),
        pub_b64=b64enc(ks["pub"]),
    )


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json(force=True, silent=True) or {}
    try:
        logn = parse_logn(data)
        message, msg_bytes = parse_message(data)
        pub_b64 = data.get("pub_b64", "")
        sig_b64 = data.get("signature_b64", "")
        if not pub_b64 or not sig_b64:
            raise ValueError("pub_b64 and signature_b64 are required")
        pub = b64dec(pub_b64)
        sig = b64dec(sig_b64)
    except ValueError as exc:
        return jsonify(error=str(exc), valid=False), 400

    # A malformed-but-well-sized key or signature is a verification failure, not a
    # server error: the decoders return None or raise on garbage input.
    try:
        valid = bool(hawkverify(logn, pub, msg_bytes, sig))
    except Exception:
        valid = False

    return jsonify(valid=valid, message=message, variant=f"Hawk-{1 << logn}")


@app.route("/api/clients", methods=["GET"])
def api_clients():
    clients = [
        {
            "client_id": cid,
            "logn": ks["logn"],
            "variant": f'Hawk-{1 << ks["logn"]}',
            "pub_b64": b64enc(ks["pub"]),
        }
        for cid, ks in key_store.items()
    ]
    return jsonify(clients=clients)


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(status="ok", clients=len(key_store))


if __name__ == "__main__":
    print("Hawk PQC demo server -> http://127.0.0.1:5050")
    print("WARNING: Hawk is cryptographically broken. Demo only, never for real use.")
    app.run(host="127.0.0.1", port=5050, debug=False)
