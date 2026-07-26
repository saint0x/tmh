# TMH

Tiered Memory Hierarchy (TMH) is a pressure-aware KV layout for transformer inference. This repo is the standalone research and validation POC. Production integration lives in SOCK:

- Production runtime: [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock)
- Production layout flag: `--kv-layout tmh`
- Current production model path: vLLM physical TMH KV on ROCm for `Qwen/Qwen3-30B-A3B-GPTQ-Int4`

## Current TMH Contract

TMH models four KV roles:

| Role | Storage intent |
| --- | --- |
| `PINNED_RAW` | anchor KV |
| `HOT_RAW` | active tail KV |
| `WARM_INT8_INT4` | compressed early-layer KV |
| `WARM_INT8_INT8` | compressed late-layer KV |

SOCK contains the production vLLM path.

## Proven Results

Production results on `Qwen/Qwen3-30B-A3B-GPTQ-Int4`:

| Benchmark | Result |
| --- | ---: |
| KV token capacity at util0.35 | `+73.82%` vs standard |
| Max concurrency at util0.35, 8k context | `+73.79%` vs standard |
| Max concurrency at util0.35, 16k context | `+73.90%` vs standard |
| All-raw live saturation control at c12 | `-2.07%` vs standard total tok/s |
| Adaptive-raw live saturation at c12, hot25 | preserves `+73.51%` capacity while improving the hot25 live path |
| Best current physical TMH runtime | `+2.12%` vs the prior physical TMH pass |

See [RESULTS.md](RESULTS.md) for the validation boundary. For exact benchmark tables and raw measurements, see [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock).

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

Install the Fzy compiler from [saint0x/fzy](https://github.com/saint0x/fzy) to build or extend the standalone POC. The commands below validate the checked-in contract and artifacts.

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

The Fzy source is a compact POC model validated by the scenarios and artifact validators above.

## Boundary

This repo is the research POC and reproducible contract suite. The production implementation and latest performance work are in [ariacomputecompany/sock](https://github.com/ariacomputecompany/sock).

The honest current thesis:

> TMH increases KV capacity materially and continues to improve throughput on the production ROCm path.
