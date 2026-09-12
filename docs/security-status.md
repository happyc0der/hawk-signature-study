# Security status: Hawk is broken

> **Hawk is insecure and must not be used for anything.** It was withdrawn from NIST's
> Additional Digital Signatures standardisation process on **29 July 2026**.

This page records what happened, because the report and slides in this repository were
written in June 2026 — about seven weeks before the break — and describe Hawk as a healthy
Round 3 candidate. Rather than rewrite them, they are kept as submitted and this page
documents what changed.

## Timeline

| Date | Event |
|------|-------|
| Feb 2025 | Hawk v1.1 round-2 specification submitted to NIST |
| 14 May 2026 | NIST IR 8610: nine schemes advance to Round 3; Hawk is the only lattice-based one |
| 8 June 2026 | This course project submitted ([report](hawk-report.pdf), [slides](../web/presentation.html)) |
| 28 July 2026 | Straznickas & Weis publish the key-recovery reduction; independently verified on the pqc-forum the same day |
| 29 July 2026 | Hawk team withdraws the submission; hawk-sign.info states "Hawk is insecure and should not be used" |

## The attack

**Straznickas, Z. and Weis, S. A. — *Hawk-n Key Recovery Reduces to SVP in Dimension n/2 + 1*,
IACR ePrint 2026/1593** ([paper](https://eprint.iacr.org/2026/1593)).

The result is an *unconditional, deterministic polynomial-time reduction* from Hawk-n key
recovery over K_n = Q(ζ_2^ℓ) to poly(n) calls to an exact-SVP oracle in dimension **n/2 + 1**
— roughly half the dimension the parameters were sized against.

The chain of ideas:

1. **A nontrivial automorphism of the key lattice exists.** It comes from the Galois
   involution τ : ζ ↦ −ζ on the power-of-two cyclotomic field.
2. **It is publicly recoverable.** The automorphism appears as a shortest vector of a public
   rank-n lattice that is isometric, up to scaling, to Z^(n/2+1) ⊕ √2·Z^(n/2−1) — a
   "near-hypercubic" lattice on which Ducas's block reduction finds short vectors efficiently.
3. **The automorphism collapses the problem.** The descent of van Gent and Pulles then
   recovers the secret basis from it, so the attacker never has to reduce the full
   dimension-2n lattice that the security estimates assumed.

Note what this is *not*: it is not a heuristic, not a quantum attack, and not specific to a
weak parameter choice. It is a structural property of the ring Hawk chose.

### Concrete cost

Headline figures, as stated in the paper's abstract — total key-recovery cost against the
specification's own claims:

| Variant | Claimed | After the attack |
|---------|---------|------------------|
| Hawk-512 (NIST level I) | 2^150 | **2^108** |
| Hawk-1024 (NIST level V) | 2^288 | **2^182** |

The paper's §6 table breaks this down by cost model — BKZ blocksize, Core-SVP gates, and
AGPS20 gates:

| Variant | β (spec → attack) | Core-SVP (spec → attack) | AGPS20 (spec → attack) |
|---------|-------------------|--------------------------|------------------------|
| Hawk-256 † | 211 → 129 | 2^62 → 2^38 | 2^74 → 2^52 |
| Hawk-512 | 452 → 257 | 2^132 → 2^75 | 2^141 → 2^86 |
| Hawk-1024 | 940 → 513 | 2^274 → 2^150 | 2^278 → 2^158 |

† Hawk-256 is a *challenge* parameter set; the specification states no gate count for it, so
the "spec" figures here are the attack authors' own computation. It is the set that was
actually broken: the authors recovered the secret keys of two Hawk-256 public keys produced
by the reference key generator, end-to-end, in a few hours on a single server.

Hawk-512 and Hawk-1024 are not practically breakable today, but they no longer meet the NIST
level I and level V claims they were submitted under, and the roughly halved blocksize is
what makes the gap unrecoverable without changing parameters.

### Why it was not repaired

Restoring the original security margin would require roughly doubling parameters, or moving
to higher-rank modules. Either change erases the compactness and speed that made Hawk
interesting next to the already-standardised ML-DSA and FN-DSA. The Hawk team's own
withdrawal notice makes this point: naive fixes "make Hawk uncompetitive compared to other
(standardized) lattice candidates." Withdrawal was cheaper than repair.

### Scope

- **Falcon is unaffected.** The construction does not transfer to it.
- **ML-DSA (Dilithium) and FN-DSA (Falcon) are unaffected.** They rest on SIS/LWE, not
  module-LIP, and are the algorithms to actually deploy.
- **Conductors m ∈ {p^k, 2p^k}** for odd prime p — the m > 4 with cyclic (Z/m)^× — evade the
  attack. The weakness is tied to the automorphism structure of power-of-two cyclotomics,
  not to lattice signatures in general.
- **No deployed system was affected.** Hawk was a candidate, never a standard.

## What the June 2026 report got right and wrong

The report's §5 and §9 identified the correct risk and located it correctly:

> "The primary open question is the long-term hardness of smLIP over CM-fields."

and flagged that the practical security case rested on BKZ experiments rather than a tight
reduction — "a methodological gap." It listed the 2024–2025 smLIP results (Miller et al. on
totally real fields; Cohn–Fehr–Menezes; Lee et al. on symplectic automorphisms) as the live
threat, and noted NIST had encouraged further analysis of exactly these assumptions.

What it did not anticipate is that the CM-field case would fall this quickly, and that the
lever would be an automorphism recoverable from public data alone. The report's conclusion
that Hawk was "poised for standardisation if the CM-field smLIP assumption withstands
ongoing scrutiny over the next two years" is the sentence the attack answered — in seven
weeks rather than two years.

## Sources

- Straznickas & Weis, [*Hawk-n Key Recovery Reduces to SVP in Dimension n/2 + 1*](https://eprint.iacr.org/2026/1593), IACR ePrint 2026/1593, 28 July 2026
- [pqc-forum announcement and independent verification](https://groups.google.com/a/list.nist.gov/g/pqc-forum/c/2r2u6SbHun4)
- [hawk-sign.info](https://hawk-sign.info/) — withdrawal notice, 29 July 2026
- Moody et al., [NIST IR 8610](https://csrc.nist.gov/pubs/ir/8610/final) — second-round status report, May 2026
- Ducas, Postlethwaite, Pulles, van Woerden, [*Hawk: Module LIP makes Lattice Signatures Fast, Compact and Simple*](https://eprint.iacr.org/2022/1155), ASIACRYPT 2022
