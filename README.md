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

SOCK has validated TMH on the production `Qwen/Qwen3-30B-A3B-GPTQ-Int4` path across capacity, live saturation, and physical-runtime bring-up:

| Benchmark | Result |
| --- | ---: |
| KV token capacity at util0.35 | `+73.82%` vs standard |
| Max concurrency at util0.35, 8k context | `+73.79%` vs standard |
| Max concurrency at util0.35, 16k context | `+73.90%` vs standard |
| All-raw live saturation control at c12 | `-2.07%` vs standard total tok/s |
| Adaptive-raw live saturation at c12, hot25 | preserves `+73.51%` capacity while improving the hot25 live path |
| Best current physical TMH runtime | `+2.12%` vs the prior physical TMH pass |

This standalone repo preserves the contract and reproducible validation boundary behind those production runs:

| Validation | Result |
| --- | ---: |
| Qwen-30B old/warm KV pressure reduction | `16.667%` |
| model-family old/warm KV pressure floor | `16.071%` |
| paper-claim stress rows | `732,000` |
| adversarial checked layer-pages | `356,890,836` |

Read [RESULTS.md](RESULTS.md) for the full evidence boundary. For exact benchmark tables and raw production measurements, see [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock).

## Repository Layout

```text
src/                  Fzy POC for page roles, planning, runtime accounting, and smoke execution
standalone_harness/   Python validators and Fozzy scenarios
artifacts/            frozen reports, JSON outputs, and recorded Fozzy traces
TMH.md                architecture and implementation map
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

> TMH is validated as a memory hierarchy abstraction. In SOCK, it materially expands KV capacity, keeps all-raw live serving near standard throughput, completes the c14 live frontier with fallback, and continues to improve the physical mixed-fidelity runtime on the production ROCm path.
