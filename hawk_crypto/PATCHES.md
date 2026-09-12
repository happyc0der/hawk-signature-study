# Changes to the vendored hawk-py code

This directory is a vendored copy of [hawk-sign/hawk-py](https://github.com/hawk-sign/hawk-py)
(MIT), the Python implementation that accompanies the Hawk v1.1 specification. It is kept
verbatim apart from the changes listed here, so that the code can be diffed against upstream.

Everything below is a correctness or packaging fix. No parameter, algorithm, or encoding was
altered.

## 1. NumPy 2 integer promotion (`codec.py`)

Under NumPy ≥ 2 ([NEP 50](https://numpy.org/neps/nep-0050-scalar-promotion.html)) a Python
int combined with a NumPy scalar no longer widens the result — the NumPy dtype wins. Both
sites below received `uint8` values read out of a bit array from `np.unpackbits`, which made
the whole computation `uint8`.

- `decodeint` accumulated `c += x[...]`, so `c` became a `uint8` after the first term.
  `decompressgr` then computed `x[i] + z * 2**low`, which raised
  `OverflowError: Python integer 256 out of bounds for uint8` and made **every verification
  fail** on NumPy 2. Fixed by casting the bit to `int` before accumulating.
- `decompressgr`'s sign-bit application `x[i] - y[i] * (2 * x[i] + 1)` overflowed `uint8`
  and emitted `RuntimeWarning: overflow encountered in scalar subtract`. Fixed with
  `int(y[i])`.

On NumPy 1.x the first issue wrapped silently rather than raising, so the original code only
worked by accident there.

## 2. Bounds check in `decompressgr` (`codec.py`)

The Golomb–Rice unary-decoding loop read:

```python
if j >= len(y) and z >= 2 ** (high - low):
    return None
```

Algorithm 7 of the specification, and the comment directly above the code, both say **or**.
With `and`, a bit sequence that runs out before the terminating `1` bit falls through to
`t = y[j]` and raises `IndexError`. Random 249-byte inputs hit this reliably. Changed to
`or`, so malformed input is rejected as `⊥` (returned as `None`) the way the spec requires.
Covered by `tests/test_hawk.py::test_random_signatures_rejected_without_raising`.

## 3. Length check in `decode_public` (`codec.py`)

```python
if len(y) * 8 < j + v:   # was
if len(y) < j + v:       # now
```

`y` is already a bit array (`np.unpackbits` output), so multiplying by 8 again compared bits
against eight times the bit length and the check could never fire. Algorithm 9 specifies
`len_bits(y) < j + v`. Valid keys are unaffected — the condition is slack for them — but
truncated keys were silently decoded instead of rejected.

## 4. Package imports

Upstream uses top-level absolute imports (`from poly import ...`) that only resolve when the
package directory itself is on `sys.path`, which is why the original `app.py` did a
`sys.path.insert`. Converted to explicit relative imports (`from .poly import ...`) so
`hawk_crypto` is importable as an ordinary package from the repository root.

Consequent changes:

- `keygen.py`: `import ntrugen` + `ntrugen.fft.inv_fft(...)` relied on `ntrugen.fft` having
  been registered as a side effect of another module's import. Replaced with a direct
  `from .ntrugen.fft import inv_fft`.
- `__init__.py` re-exports `hawkkeygen`, `hawksign`, `hawkverify`.
- Removed two unused imports: `sympy.ntheory.npartitions` in `verify.py` and `random` in
  `ntrugen/ntrugen_hawk.py`.

## Known upstream limitations, left as-is

- The Python implementation uses floating-point arithmetic in key generation and is, in
  upstream's words, "not compliant with the reference implementation / specifications." The
  C reference implementation is the normative one.
- Nothing here is constant-time. The whole point of Hawk's design was isochronous execution;
  this code does not deliver it and is not meant to.
