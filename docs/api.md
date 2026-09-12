# REST API reference

`app.py` serves both the JSON API and the demo page on `http://127.0.0.1:5050`.
All request and response bodies are JSON. Keys and signatures are base64 of the raw
encoded byte strings.

> The server stores private keys in plaintext in process memory and has no
> authentication. It binds to `127.0.0.1` deliberately. Do not change that, and do not put
> it behind a public address — quite apart from Hawk itself being broken.

## Conventions

| Field | Meaning |
|-------|---------|
| `logn` | log₂ of the ring degree: `8` → Hawk-256, `9` → Hawk-512 (default), `10` → Hawk-1024 |
| `client_id` | Arbitrary string naming a key pair held server-side. Defaults to `"default"` |
| `message` | UTF-8 string, at most 4096 bytes encoded |

Errors return a non-2xx status with `{"error": "..."}`.

---

## `POST /api/keygen`

Generates a key pair and stores it under `client_id`, replacing any existing one.
This is the slow call: seconds for Hawk-256/512, minutes for Hawk-1024.

**Request**

```json
{ "client_id": "alice", "logn": 9 }
```

**Response `200`**

```json
{
  "client_id": "alice",
  "logn": 9,
  "variant": "Hawk-512",
  "pub_b64": "...",
  "priv_len": 184,
  "pub_len": 1024,
  "message": "Key pair generated successfully"
}
```

The private key is never returned — it stays server-side and is used by `/api/sign`.

**`400`** if `logn` is not 8, 9, or 10.

---

## `POST /api/sign`

Signs a message with the stored private key for `client_id`.

**Request**

```json
{ "client_id": "alice", "message": "attack at dawn" }
```

**Response `200`**

```json
{
  "client_id": "alice",
  "logn": 9,
  "variant": "Hawk-512",
  "message": "attack at dawn",
  "signature_b64": "...",
  "sig_len": 555,
  "pub_b64": "..."
}
```

`pub_b64` is echoed back so a client can hand the verifier everything it needs in one step.

**`400`** if no key pair exists for `client_id`, or the message exceeds 4096 bytes.

---

## `POST /api/verify`

Verifies a signature. Stateless — needs no stored key, so it models the recipient's side.

**Request**

```json
{
  "logn": 9,
  "message": "attack at dawn",
  "pub_b64": "...",
  "signature_b64": "..."
}
```

**Response `200`**

```json
{ "valid": true, "message": "attack at dawn", "variant": "Hawk-512" }
```

A well-formed request with a bad signature, a tampered message, a mismatched public key, or
undecodable key/signature bytes returns `200` with `"valid": false`. Only a malformed
*request* — missing fields, bad base64, unsupported `logn` — returns `400`.

---

## `GET /api/clients`

Lists the key pairs currently held in memory.

```json
{ "clients": [ { "client_id": "alice", "logn": 9, "variant": "Hawk-512", "pub_b64": "..." } ] }
```

---

## `GET /api/status`

Health check used by the demo page's connection indicator.

```json
{ "status": "ok", "clients": 1 }
```

---

## Example session

```bash
curl -X POST http://127.0.0.1:5050/api/keygen \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"alice","logn":8}'

curl -X POST http://127.0.0.1:5050/api/sign \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"alice","message":"attack at dawn"}'

# paste pub_b64 and signature_b64 from the previous response
curl -X POST http://127.0.0.1:5050/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"logn":8,"message":"attack at dawn","pub_b64":"...","signature_b64":"..."}'
```
