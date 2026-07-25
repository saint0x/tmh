# TMH Optimization Ledger

This is a concise public ledger of the production optimization path. The full raw lab notebook lives in SOCK’s `OPTIMIZATIONS.md`.

Production implementation: [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock)

## 1. Baseline Problem

Early physical TMH was functional but throughput-negative. The bad c12 point was:

```text
TMH c12 before native raw/refcount: wall=489.0607s p50=329.8101s p90=488.7363s total_tok/s=171.3223
```

This was not acceptable. TMH had capacity value, but the runtime path was too slow.

## 2. Canonical Descriptor Refcount Fix

The main c12 bottleneck was completion-time descriptor release. The old release path scanned active descriptors to decide whether canonical pages were still referenced. With 7K-token prompts, pages times layers repeated per descriptor became quadratic CPU work.

Fix:

- maintain canonical descriptor refcounts
- increment/decrement when canonical descriptor keys appear or change
- emit release events only when the final reference disappears

Result:

```text
TMH c4 before: 259.0873 tok/s
TMH c4 after:  1184.1359 tok/s
Standard c4:   1022.0045 tok/s

TMH c12 before: 171.3223 tok/s
TMH c12 after:  1045.2849 tok/s
Standard c12:   1023.9407 tok/s
```

Relative movement:

```text
c4 TMH after vs standard:  +15.86%
c12 TMH after vs standard: +2.08%
c12 TMH after vs old TMH: +510.13%
```

## 3. Overlay Raw Exhaustion Fallback

After the refcount fix, c14 exposed raw pool exhaustion in request-overlay pages:

```text
c14 before fallback: failed=14
error: TMH physical raw pool is exhausted
```

Fix:

- if a request-overlay raw page wants a raw slot and the raw pool is empty, demote that descriptor to the layer-appropriate warm role
- early layers demote to `WARM_INT8_INT4`
- late layers demote to `WARM_INT8_INT8`

Result:

```text
TMH c14 overlay fallback: wall=96.6954s p50=62.2219s p90=96.6604s total_tok/s=1010.9373 ok=14 failed=0
```

## 4. Canonical Raw Exhaustion Fallback

A larger BT16384 c14 probe then exposed the same hard failure in canonical hot raw pages:

```text
BT16384 before fallback: wall=20.5495s total_tok/s=339.7643 ok=1 failed=13
```

Fix:

- if an existing canonical raw slot exists, keep sharing it
- if a raw slot is available, keep the fast raw path
- if the raw pool is exhausted, demote only the new canonical descriptor to the warm role
- release logic checks the warm fallback key so demoted slots do not leak

Result:

```text
BT16384 after canonical fallback: wall=108.3874s p50=68.4651s p90=108.3815s total_tok/s=901.8857 ok=14 failed=0
```

This is a robustness win, not a throughput win. BT8192 remains the better c14 shape.

## 5. Rejected Warmmix Warmup

A long-shape TMH warmup was tested because BT16384 still showed inference-time JIT for mixed TMH kernels.

Result:

```text
BT16384 canonical fallback: 901.8857 tok/s
BT16384 warmmix warmup:    901.9173 tok/s
```

The change added startup time, did not remove the relevant JIT warnings, and did not materially improve throughput. It was reverted.

## Current Target

The remaining bottleneck is c14+ active-step work under raw pressure. The next likely optimization directions are:

- admission/raw-reserve shaping
- faster warm mixed-attention execution
- lower descriptor application overhead in high-pressure steps
