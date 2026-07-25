# TMH

Tiered Memory Hierarchy (TMH) is a research implementation of a pressure-aware KV cache layout for transformer inference.

The core idea is simple: KV cache pages do not all have the same runtime value. Prompt anchors, recent decode tail pages, older early-layer pages, and older late-layer pages should not be forced into one uniform representation. TMH makes those roles explicit so a runtime can choose residency and fidelity before memory pressure turns into eviction or failed admission.

This repository is the standalone research and Fozzy-validation POC. The production integration lives in SOCK:

- Production runtime: [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock)
- Production layout flag: `--kv-layout tmh`
- Current production model path: vLLM physical TMH KV on ROCm for `Qwen/Qwen3-30B-A3B-GPTQ-Int4`

## Current TMH Contract

The current implementation models four physical KV roles:

| Role | Storage intent |
| --- | --- |
| `PINNED_RAW` | first/page-anchor KV, kept raw |
| `HOT_RAW` | recent active tail KV, kept raw |
| `WARM_INT8_INT4` | older early-layer KV, int8 K plus int4 V |
| `WARM_INT8_INT8` | older late-layer KV, int8 K plus int8 V |

The standalone Fzy code and Python harnesses validate this layout contract. SOCK contains the real vLLM implementation: physical raw and warm pools, descriptor application, raw/warm cache writers, mixed attention kernels, prefix-cache-aware storage, and raw-pressure fallback behavior.

## Proven Results

The strongest current production result is no longer the early POC memory-only claim. SOCK now has a real physical TMH path that is throughput-positive at the validated operating point:

| Benchmark | Result |
| --- | ---: |
| TMH c4 vs standard c4 | `+15.86%` total tok/s |
| TMH c12 vs standard c12 | `+2.08%` total tok/s |
| TMH logical KV capacity at util0.35 | `+73.51%` vs standard |
| c14 frontier after fallback | succeeds `14/14` instead of engine-dead |

The standalone repo still preserves the older reproducible layout evidence:

| Validation | Result |
| --- | ---: |
| Qwen-30B old/warm KV pressure reduction | `16.667%` |
| model-family old/warm KV pressure floor | `16.071%` |
| paper-claim stress rows | `732,000` |
| adversarial checked layer-pages | `356,890,836` |

Read [RESULTS.md](RESULTS.md) for the full evidence boundary.

## Repository Layout

```text
src/                  Fzy POC for page roles, planning, runtime accounting, and smoke execution
standalone_harness/   Python validators and Fozzy scenarios
artifacts/            frozen reports, JSON outputs, and recorded Fozzy traces
TMH.md                architecture and implementation map
SPEC.md               standalone contract and invariants
RESULTS.md            current production plus POC evidence
OPTIMIZATIONS.md      concise SOCK optimization ledger
TMHSTORY.md           short project history
```

## Quickstart

Install the Fzy compiler from [saint0x/fzy](https://github.com/saint0x/fzy) if you want to build or extend the standalone Fzy POC sources directly. The commands below validate the checked-in TMH contract and artifacts.

Run the core deterministic layout validator:

```bash
fozzy --json run standalone_harness/tmh_only_30b_layout.fozzy.json --det --strict --seed 1337
```

Run the model-family validation:

```bash
fozzy --json run standalone_harness/tmh_model_family_memory_baseline.fozzy.json --det --strict --seed 1337 --proc-backend host --fs-backend host
```

Verify and replay a recorded trace:

```bash
fozzy trace verify artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy --strict --json
fozzy replay artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy --json
fozzy ci artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy --json
```

The Fzy source is intentionally kept as a compact POC model. In this repository it is validated through the Fozzy scenarios and Python artifact validators above; use the public [Fzy compiler](https://github.com/saint0x/fzy) for direct compiler work.

## Boundary

This repo should be read as the research POC and reproducible contract suite. It is intentionally not presented as the production serving engine. The production implementation and latest performance work are in [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock).

The honest current thesis:

> TMH is validated as a memory hierarchy abstraction and is now throughput-positive in the production SOCK/vLLM path at the best tested operating point, while c14+ still needs more active-step optimization to turn capacity headroom into a larger throughput win.
