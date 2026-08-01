# 5. Experimental Methodology

The evaluation separates three questions that are easy to blur together: how many pages fit, whether old information remains useful, and how the physical path performs inside a server. A fourth question—numerical fidelity of the physical INT4 kernel—cannot be answered by the available measurements because of the defect described in Section 4.5.

## 5.1 Layout and capacity

Capacity is evaluated at two levels. An analytical model counts payload bytes under the four-role policy. The physical allocator adds FP32 scales, per-page descriptors, anchor reserve, integral pool sizes, and the finite device budget.

Three geometry sets are used:

- a 48-layer Qwen3-30B profile with four KV heads, head dimension 128, and 16-token pages;
- an adversarial matrix of 16,632 configurations spanning five synthetic model shapes, page sizes from 1 to 512, twelve raw-budget settings, and 21 sequence cases; and
- fifteen cached decoder configurations producing 18,600 base layouts, expanded with traffic variations to 732,000 layouts, 682,050 of which contain an old body.

For each layout we record page coverage, overlap, anchor placement, tail placement, early/late warm assignment, and bytes relative to two baselines: all-BF16 storage and a same-hot layout with uniformly INT8 old keys and values. Configurations without old pages are excluded from old-body percentage summaries.

## 5.2 Retention study

The policy study asks whether a compressed old body is preferable to discarding it. Fixed fact-recall prompts are run on Qwen2.5-1.5B-Instruct (250 examples), SmolLM2-1.7B-Instruct (60), and Granite-3.3-2B-Instruct (60). Four cache policies are compared:

- full KV;
- recent-only KV, which removes the old body;
- uniformly quantized old KV; and
- fidelity paging, which retains the anchor and tail in raw form and applies layer-dependent precision to the old body.

Compressed policies use hot budgets of 50%, 25%, 12.5%, 6.25%, and 0%. The reported metrics are exact-or-prefix match and target containment. The experiment runs model inference, but the cache behavior is emulated at policy level. It does not call the Triton writer evaluated in the serving study. The result can support a claim about retaining old evidence; it cannot support a claim about the quality of the physical INT4 format.

## 5.3 Serving platform

The main endpoint experiment uses the configuration in Table 2.

**Table 2. Production serving configuration.**

| Component | Configuration |
|---|---|
| host | GMKtec EVO-X2 |
| accelerator | AMD Strix Halo / Radeon 8060S (`gfx1151`) |
| runtime | ROCm 7.2.4 |
| model | Qwen3-30B-A3B-GPTQ-Int4 |
| attention | grouped-query causal decoder attention |
| maximum sequence length | 2,048 tokens |
| maximum active sequences | 4 |
| maximum batched tokens | 1,024 |
| GPU memory utilization | 0.35 |
| execution mode | eager |
| TMH raw budget | 25% |
| endpoint | OpenAI-compatible completions |

Six prompts exercise different generation lengths and input shapes. Each case runs at concurrency 1, 2, and 4, producing eighteen cells (Table 3).

**Table 3. Endpoint workload classes.**

| Case | Prompt character | Maximum completion |
|---|---|---:|
| tiny fact | short factual explanation | 64 tokens |
| short code generation | compact Python function and complexity discussion | 128 |
| medium architecture | production job-queue design | 256 |
| long cosmology | long-form scientific explanation | 512 |
| long-context summary | repeated operational context followed by summarization | 256 |
| extended generation | technical essay on heterogeneous serving runtimes | 768 |

Requests use temperature 0.2. Each cell has one warmup batch and two timed batches. Standard KV and TMH use the same endpoint code, prompts, concurrency, and model settings. Completion tokens per second is the primary metric. Suite duration is retained as a coarse end-to-end check but not combined with token throughput.

We report the geometric mean across the eighteen throughput ratios because absolute token rates vary considerably by prompt. Per-cell results are also shown; the aggregate alone would hide the long-context summarization regression.

## 5.4 Physical implementations

The serving comparison contains four layouts or kernel stages:

1. standard homogeneous KV;
2. the first physical TMH kernel;
3. an optimized TMH kernel with page-aligned tiles, raw/warm tile handling, and reuse of the request-row map; and
4. a page-descriptor variant that loads role and slot once per physical page.

The fourth stage is the final preserved implementation. Separate CUDA experiments study launch shape, packed-value decomposition, and segmented decode, but they use a different device and model and are not pooled with the AMD result.

## 5.5 Numerical evidence

Available comparisons against dense attention use nominal absolute tolerances near 0.05 for raw paths and absolute/relative tolerances of 0.35 for mixed and segmented paths. Their records do not state the error statistic, tensor population, trial count, or activation distribution. More importantly, the comparisons did not expose the sign-definite INT4 failure.

We therefore do not present the thresholds as a numerical-accuracy result. A defensible evaluation of the corrected writer should report distributions of maximum and mean error by layer, head, sequence length, and vector sign pattern, followed by end-to-end logit and task measurements. No such distribution is available for the benchmark revision.

## 5.6 Statistical treatment

Two timed batches per cell are too few for confidence intervals or claims about sub-percent changes. The 0.73% page-descriptor difference and 0.85% CUDA launch difference are retained as local observations, not general speedups. The 18.33% gap to standard KV is large and appears across most workload cells, but its precise magnitude should still be confirmed with more repetitions.

Later notes report positive throughput after changes to canonical reference accounting and pool fallback. Their implementation revision was not preserved. Those numbers are excluded from the abstract, headline result, and main performance tables.
