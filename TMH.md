# TMH Architecture

TMH means Tiered Memory Hierarchy.

The architecture starts from one observation: KV cache pages are not uniform. A recent decode tail page, the first prompt page, and an old early-layer page have different latency, reuse, and fidelity requirements. A flat KV cache hides those differences until the runtime runs out of memory.

TMH makes those differences explicit.

## Standalone POC

The Fzy implementation in this repo is a compact executable model of the TMH contract:

```text
src/kv/          page table, logical block table, allocator, policy model
src/runtime/     session, prefill/decode loop, residency, sharing/COW model
src/attention/   full, recent-only, and fidelity-aware attention variants
src/model/       model-shape and artifact inspection helpers
src/bench/       deterministic benchmark/report primitives
```

It is intentionally small. It is useful for validating policy, invariants, memory accounting, and deterministic harness behavior.

## Production Implementation

The real runtime implementation is in SOCK’s vendored vLLM path:

[https://github.com/ariacomputecompany/sock](https://github.com/ariacomputecompany/sock)

Current production pieces include:

- `TMHFullAttentionSpec` memory planning
- physical TMH KV allocation
- raw KV pool plus warm compressed pool
- scheduler-emitted physical descriptor events
- canonical descriptor refcounts
- request-overlay slots for prefix-cached hot raw pages
- overlay raw exhaustion fallback
- canonical raw exhaustion fallback
- TMH raw and warm cache update kernels
- TMH mixed attention kernel
- native all-raw fast paths where the TMH layout degenerates to standard KV

## Runtime Flow

```text
request tokens
  -> page geometry
  -> TMH hot/warm role plan
  -> physical descriptors
  -> worker applies descriptors
  -> cache update writes raw or warm page storage
  -> attention reads raw/warm physical slots
  -> release path decrements canonical descriptor refs
```

The latest production optimization work found that descriptor lifetime tracking matters as much as kernel math. A quadratic canonical-release scan was the main c12 bottleneck until it was replaced with maintained descriptor refcounts.

## Why This Is A Memory Hierarchy

TMH is not just "KV quantization." Quantization is one mechanism inside a broader hierarchy:

- role: anchor, hot tail, old early, old late
- fidelity: raw, int8/int4, int8/int8
- storage kind: canonical shared page or request overlay
- pressure behavior: raw when useful, demote when raw pool pressure rises
- runtime path: native raw fast path or mixed TMH path

The contribution is the explicit hierarchy and its runtime contract.
