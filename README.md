# Hawk: a post-quantum signature scheme, and how it broke

> [!CAUTION]
> **Hawk is cryptographically broken.** It was withdrawn from NIST's Additional Digital
> Signatures standardisation process on 29 July 2026, after a polynomial-time reduction took
> Hawk-*n* key recovery to SVP in dimension *n*/2 + 1. Nothing in this repository should be
> used to protect anything. See [docs/security-status.md](docs/security-status.md).

A course project for **CS-UY 3943, Post-Quantum Cryptography** (NYU Tandon, Spring 2026,
Prof. Dr. Delaram Kahrobaei) — a written study of Hawk, a talk, and a working demo of key
generation, signing, and verification over a REST API.

It is published as an archive. The report and slides were submitted on 8 June 2026, seven
weeks before the attack landed; they describe Hawk as a healthy NIST Round 3 candidate,
which it was at the time. They are kept unedited, with the break documented separately.

## What's here

| Path | |
|------|--|
| [`docs/hawk-report.pdf`](docs/hawk-report.pdf) | The report: algorithms, parameters, security reductions, cryptanalysis (13 pages) |
| [`docs/security-status.md`](docs/security-status.md) | **The break** — what the attack does, concrete costs, what it means |
| [`docs/api.md`](docs/api.md) | REST API reference |
| [`web/presentation.html`](web/presentation.html) | The talk, as given (self-contained HTML deck) |
| [`web/demo.html`](web/demo.html) | Interactive demo: keygen, sign, verify, and an Alice→Bob walkthrough |
| [`app.py`](app.py) | Flask server — serves the JSON API and the demo page |
| [`hawk_crypto/`](hawk_crypto/) | Hawk reference implementation, vendored from [hawk-sign/hawk-py](https://github.com/hawk-sign/hawk-py) ([changes](hawk_crypto/PATCHES.md)) |
| [`tests/`](tests/) | Round-trip and malformed-input tests |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5050** — the server hosts the demo page itself, so there is
nothing to configure. The slide deck is at `/presentation.html`.

Signing a message end-to-end from the command line:

```bash
curl -X POST http://127.0.0.1:5050/api/keygen -H 'Content-Type: application/json' -d '{"client_id":"alice","logn":8}'
curl -X POST http://127.0.0.1:5050/api/sign   -H 'Content-Type: application/json' -d '{"client_id":"alice","message":"attack at dawn"}'
```

Or use the library directly:

```python
import numpy as np
from hawk_crypto import hawkkeygen, hawksign, hawkverify

priv, pub = hawkkeygen(9)                                  # Hawk-512
msg = np.frombuffer(b"attack at dawn", dtype=np.uint8)
sig = hawksign(9, priv, msg)
assert hawkverify(9, pub, msg, sig)
```

## How Hawk worked

Hawk is a hash-and-sign lattice signature over the power-of-two cyclotomic ring
R_n = Z[X]/(X^n + 1).

- **Private key** — a short unimodular basis `B = [[f, F], [g, G]] ∈ GL₂(R_n)`, with
  `f, g` sampled from a centred binomial distribution and `F, G` obtained by solving the
  NTRU equation `fG − gF = 1`. The encoded form stores only a seed plus `F mod 2` and
  `G mod 2`, which is why private keys are so small.
- **Public key** — the Gram matrix `Q = B*B`, transmitted as the polynomials
  `q₀₀ = ff* + gg*` and `q₀₁ = Ff* + Gg*`.
- **Signing** — hash the message with SHAKE-256 to a target `(h₀, h₁)`, then sample a short
  lattice vector in that coset from two fixed discrete Gaussian tables. No floating point,
  no key-dependent branching.
- **Verification** — reconstruct `s₀` from the signature and public key with 32-bit integer
  arithmetic, then check a norm bound under the Q-norm.

The design's selling points were compactness and implementability: Hawk-512 signatures are
555 bytes against Falcon-512's 666, key generation is the only expensive operation, and no
stage needs an FPU — which made it the unusual lattice scheme that fits a microcontroller.

**Security rested on module-LIP**: recovering the private key from `Q` is an instance of the
search module Lattice Isomorphism Problem, and forgery reduces to a one-more approximate SVP
problem. Those assumptions were newer than the SIS/LWE assumptions behind ML-DSA and
Falcon — the diversity that made Hawk valuable is also what made it fragile. The 2026 attack
broke module-LIP for exactly the fields Hawk chose, by finding an automorphism of the key
lattice that an attacker can recover from public data alone.

## Parameters

| Variant | n | Private key | Public key | Signature | Claimed level | Key recovery, claimed → after attack |
|---------|---|------------|-----------|-----------|---------------|--------------------------------------|
| Hawk-256 | 256 | 96 B | 450 B | 249 B | challenge set | 2^62 → **2^38** — keys actually recovered |
| Hawk-512 | 512 | 184 B | 1024 B | 555 B | NIST I | 2^150 → **2^108** |
| Hawk-1024 | 1024 | 360 B | 2440 B | 1221 B | NIST V | 2^288 → **2^182** |

Hawk-512 and Hawk-1024 figures are the paper's headline totals; Hawk-256 is in the Core-SVP
model, since the specification states no gate count for the challenge set. Full breakdown by
cost model in [docs/security-status.md](docs/security-status.md).

## Tests

```bash
pip install pytest && pytest
```

Covers sign/verify round trips, spec-conformant encoded sizes, and rejection of tampered
messages, wrong public keys, corrupted and truncated signatures, and random garbage. Hawk-256
and Hawk-512 run by default (~30s); set `HAWK_TEST_SLOW=1` to include Hawk-1024, which takes
several minutes to key-generate.

## Caveats

- **The demo server is a teaching tool.** It holds private keys in plaintext in process
  memory, has no authentication, and binds to `127.0.0.1` on purpose. Leave it there.
- **The vendored Python implementation is not constant-time** and uses floating-point
  arithmetic in key generation, so it does not match the C reference implementation
  bit-for-bit. Upstream says as much. Hawk's isochronous-execution property is a property of
  the C code, not of this.
- **Four correctness fixes were applied to the vendored code**, mostly NumPy 2 compatibility
  — without them verification fails outright on current NumPy. All are listed in
  [hawk_crypto/PATCHES.md](hawk_crypto/PATCHES.md).

## If you need a post-quantum signature

Use **ML-DSA** (FIPS 204) or **SLH-DSA** (FIPS 205), or **FN-DSA**/Falcon once finalised.
Those are standardised and unaffected by this attack, which does not transfer to Falcon and
has nothing to do with the SIS/LWE assumptions they rest on.

## Credits and licence

- Hawk was designed by Léo Ducas, Eamonn Postlethwaite, Ludo Pulles, and Wessel van Woerden;
  the v1.1 submission adds Joppe Bos, Olivier Bronchain, Serge Fehr, Yu-Hsuan Huang,
  Thomas Pornin, and Thomas Prest.
- `hawk_crypto/` is vendored from [hawk-sign/hawk-py](https://github.com/hawk-sign/hawk-py),
  MIT licensed. The C reference implementation is at
  [hawk-sign/dev](https://github.com/hawk-sign/dev).
- The attack is due to Zygimantas Straznickas and Stephen A. Weis,
  [ePrint 2026/1593](https://eprint.iacr.org/2026/1593).
- Report, slides, demo, and server by Keshav Rajput. [MIT licensed](LICENSE).
