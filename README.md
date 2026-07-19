# TMH

Transformer Memory Hierarchy (`tmh`) is a research and systems project for making transformer KV memory explicit, page-native, and pressure-aware.

The core claim is simple: transformer inference should not treat all KV state as uniform. Old context, prompt anchors, active decode tail, layer position, and memory-pressure state carry different runtime meaning. TMH turns that into a compiled memory layout that a runtime can execute rather than leaving the cache manager to infer policy after memory has already been allocated.

## What This Repo Contains

- A compact TMH/FPA implementation in `src/main.fzy`.
- A standalone benchmark harness in `standalone_harness/`.
- Deterministic Fozzy scenarios for reproducible validation.
- Curated 30B benchmark artifacts under `artifacts/`.
- Research documentation in `TMH.md`, `SPEC.md`, `RESULTS.md`, `FINDINGS.md`, `RESEARCH_BASELINE.md`, and `PAPER_DRAFT_SUPPORT.md`.

## Current Evidence

The strongest current result is a 30B served-model validation path using:

- Model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- Serving path: `sock` CLI over vendored vLLM on ROCm
- Endpoint shape: OpenAI-compatible chat completions
- Context length: `2048`
- TMH layout: `tmh_fidelity_paged_kv`

The July 19, 2026 endpoint pressure run exercised:

- `3` measured runs per prompt case
- `1` warmup run per case
- concurrency levels `1`, `2`, and `4`
- `10` streaming probes
- `796.1613s` elapsed wall time

Observed throughput:

| Concurrency | Throughput range |
| ---: | ---: |
| `1` | `28.875-30.186 tok/s` |
| `2` | `35.588-37.123 tok/s` |
| `4` | `69.126-71.287 tok/s` |

Streaming time to first token held at roughly `0.106-0.180s`.

The corresponding layout sweeps covered:

- page sizes `8`, `16`, `32`, and `64`
- hot budgets `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, and `0`
- `280` measured rows per sweep
- `1080` compiled plan ranges per sweep
- `100%` plan validation

The old/warm KV pressure reduction versus same-hot uniform-int8 old KV held at `16.667%` across the sweep. Total effective KV reduction at `0%` hot was:

| Page tokens | Total effective reduction |
| ---: | ---: |
| `8` | `16.381%` |
| `16` | `16.100%` |
| `32` | `15.553%` |
| `64` | `14.515%` |

This supports the TMH thesis under real served-model pressure, while keeping the boundary honest: the current 30B evidence proves compiled layout-pressure accounting against live sock/vendored-vLLM traffic. The next milestone is wiring TMH-managed KV internals into the live runtime and rerunning the same endpoint pressure suite.

The adversarial layout stress suite expands the geometry beyond the served 30B corpus:

- `16,632` synthetic shape/page/budget/sequence rows
- `9,255` rows with old KV present
- page sizes from `1` to `512`
- hot budgets from `100` down to `0`
- five model shapes, including Qwen-30B GQA, dense/GQA boundaries, fp32 MHA, a 70B-style shape, and a one-layer all-late boundary shape
- `356,890,836` checked layer-pages
- `100%` plan validation and `100%` invariant pass rate

The hierarchy thesis held across that matrix: no cold or dropped KV, no negative total-reduction rows where old KV exists, prompt anchors stayed pinned raw, recent tails stayed raw/hot, and old pages demoted rather than evicting. The exact `16.667%` old/warm reduction remains correctly scoped to the Qwen-30B production shape.

## Quickstart

Run the deterministic TMH smoke scenario:

```bash
fozzy --json run standalone_harness/tmh_only_30b_layout.fozzy.json --det --strict-verify --seed 1337
```

Run the stronger 30B layout sweep scenario:

```bash
fozzy --json run standalone_harness/tmh_30b_standard_runs3_layout_sweep.fozzy.json --det --strict-verify --seed 1337
```

Verify and replay the recorded stronger trace:

```bash
fozzy trace verify artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy --strict --json
fozzy replay artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy --json
fozzy ci artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy --json
```

For harness-specific commands and artifact shapes, see `standalone_harness/README.md`.

## Artifact Map

- `artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md`: strongest live sock endpoint pressure report.
- `artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md`: strongest endpoint-derived TMH layout sweep.
- `artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md`: max-fit dry-run preflight sweep.
- `artifacts/tmh_adversarial_layout_stress/robust-stress-v1/REPORT.md`: adversarial geometry/model-shape stress report.
- `artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy`: deterministic trace for the strongest layout sweep.
- `artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy`: deterministic host-backed trace for the adversarial stress validator.

## Design Principles

- Page-native first. TMH operates over page ranges rather than treating the KV cache as an opaque blob.
- Explicit plan before runtime mutation. `TMHMemoryPlan` is the authority that downstream cache management should execute.
- Mixed fidelity over blind eviction. Old KV should degrade gracefully before it disappears.
- Benchmark honesty. Docs separate proven layout-pressure evidence from future runtime-internal KV claims.
- Production ergonomics. Reproducible commands, recorded traces, and artifact-backed reports are part of the project surface.

## Current Limitation

TMH is validated as a standalone layout and pressure-accounting layer against live 30B endpoint traffic. It is not yet the active KV manager inside the live sock/vendored-vLLM runtime. The next production milestone is direct runtime integration followed by the same 30B pressure suite, plus quality/performance deltas against the current sock baseline.
