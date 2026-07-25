# TMH Spec

This spec defines the standalone TMH research contract. The production implementation in SOCK follows the same concepts but lives in vLLM runtime code.

## Objective

TMH turns KV cache management into an explicit page-role plan:

```text
tokens -> pages -> per-layer page roles -> physical storage pools -> attention reads
```

The key invariant is that old KV is demoted, not destroyed. TMH may lower fidelity for older pages, but the layout must still cover every live page needed by attention.

## Page Roles

`PINNED_RAW`

- Page `0`.
- Used for prompt anchors and high-importance initial context.
- Stored raw for both K and V.

`HOT_RAW`

- Recent tail pages selected by the hot budget.
- Stored raw for both K and V.
- Optimized for active decode and latency-sensitive reads.

`WARM_INT8_INT4`

- Older pages in early/middle layers.
- K is int8 per token/head.
- V is int4 per token/head.
- This is the main memory-pressure reduction path.

`WARM_INT8_INT8`

- Older pages in late layers.
- K and V are int8 per token/head.
- Late layers are treated more conservatively.

## Layout Rules

For a request with `total_pages` and hot budget `hot_pages`:

```text
page 0                  -> PINNED_RAW
pages before recent tail -> warm role by layer
recent tail pages        -> HOT_RAW
```

Layer split:

```text
early layers: [0, floor(2/3 * layer_count))
late layers:  [floor(2/3 * layer_count), layer_count)
```

Warm role by layer:

```text
early layer old page -> WARM_INT8_INT4
late layer old page  -> WARM_INT8_INT8
```

## Required Invariants

- Every live logical page is represented.
- No live page is silently dropped.
- Page `0` remains raw.
- Recent tail pages remain raw.
- Warm pages are canonical compressed pages, not cold/evicted pages.
- The layout must be deterministic for the same model shape, page size, hot budget, and sequence length.
- Memory accounting must distinguish hot raw bytes from warm compressed bytes.

## Production Delta

SOCK adds runtime machinery that this standalone repo models but does not fully execute:

- physical raw and warm GPU pools
- per-request descriptor streams
- canonical descriptor refcounts
- request-overlay slots for prefix-cached hot raw pages
- overlay and canonical raw exhaustion fallback to warm roles
- TMH cache writer kernels
- raw and mixed attention kernels
- vLLM scheduler integration

This repo is the reference contract and validation harness. SOCK is the production path.
