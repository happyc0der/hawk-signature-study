"""Round-trip and malformed-input tests for the vendored Hawk implementation.

Run with `pytest` from the repository root, or directly with `python tests/test_hawk.py`.
Hawk-1024 key generation takes minutes, so it is only exercised when
HAWK_TEST_SLOW=1 is set.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hawk_crypto import hawkkeygen, hawksign, hawkverify  # noqa: E402
from hawk_crypto.params import PARAMS  # noqa: E402

FAST_VARIANTS = [8, 9]
ALL_VARIANTS = FAST_VARIANTS + ([10] if os.environ.get("HAWK_TEST_SLOW") == "1" else [])

MESSAGE = np.frombuffer(b"Post-Quantum Cryptography, Spring 2026", dtype=np.uint8)


@pytest.fixture(scope="module")
def keypairs():
    """One key pair per tested variant, generated once (keygen is the slow step)."""
    return {logn: hawkkeygen(logn) for logn in ALL_VARIANTS}


@pytest.mark.parametrize("logn", ALL_VARIANTS)
def test_sign_verify_roundtrip(keypairs, logn):
    priv, pub = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    assert hawkverify(logn, pub, MESSAGE, sig) is True


@pytest.mark.parametrize("logn", ALL_VARIANTS)
def test_encoded_lengths_match_spec(keypairs, logn):
    """Encoded sizes must match the v1.1 specification's parameter table."""
    priv, pub = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    assert len(priv) == PARAMS(logn, "lenpriv")
    assert len(pub) == PARAMS(logn, "lenpub")
    assert len(sig) == PARAMS(logn, "lensig")


@pytest.mark.parametrize("logn", FAST_VARIANTS)
def test_tampered_message_rejected(keypairs, logn):
    priv, pub = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    tampered = MESSAGE.copy()
    tampered[0] ^= 0x01
    assert hawkverify(logn, pub, tampered, sig) is False


@pytest.mark.parametrize("logn", FAST_VARIANTS)
def test_wrong_public_key_rejected(keypairs, logn):
    priv, _ = keypairs[logn]
    _, other_pub = hawkkeygen(logn)
    sig = hawksign(logn, priv, MESSAGE)
    assert hawkverify(logn, other_pub, MESSAGE, sig) is False


@pytest.mark.parametrize("logn", FAST_VARIANTS)
def test_corrupted_signature_rejected(keypairs, logn):
    priv, pub = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    corrupted = sig.copy()
    corrupted[-1] ^= 0xFF
    assert hawkverify(logn, pub, MESSAGE, corrupted) is False


@pytest.mark.parametrize("logn", FAST_VARIANTS)
def test_truncated_signature_rejected(keypairs, logn):
    priv, pub = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    assert hawkverify(logn, pub, MESSAGE, sig[:-1]) is False


def test_random_signatures_rejected_without_raising(keypairs):
    """Decoding garbage must return False, not raise.

    The Golomb-Rice decoder used to read past the end of the bit array on random
    input; see hawk_crypto/PATCHES.md.
    """
    logn = 8
    _, pub = keypairs[logn]
    rng = np.random.default_rng(20260608)
    siglen = PARAMS(logn, "lensig")
    for _ in range(64):
        garbage = rng.integers(0, 256, siglen, dtype=np.uint8)
        assert hawkverify(logn, pub, MESSAGE, garbage) is False


def test_random_public_keys_rejected_without_raising(keypairs):
    logn = 8
    priv, _ = keypairs[logn]
    sig = hawksign(logn, priv, MESSAGE)
    rng = np.random.default_rng(20260609)
    publen = PARAMS(logn, "lenpub")
    for _ in range(32):
        garbage = rng.integers(0, 256, publen, dtype=np.uint8)
        assert hawkverify(logn, pub=garbage, msg=MESSAGE, sig=sig) is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
