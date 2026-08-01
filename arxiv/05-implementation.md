# 4. Implementation

## 4.1 Integration surface

The prototype is implemented in a vLLM-derived serving stack [@kwon2023pagedattention; @vllmsoftware]. TMH adds a cache specification, per-layer physical pools, descriptor state, scheduler-to-worker events, a representation-aware cache-update kernel, and a Triton attention kernel [@tillet2019triton]. The request API and logical block allocator remain unchanged.

The supported attention geometry is deliberately narrow: causal decoder attention with equal key and value head dimensions. Sliding-window attention, cross-attention, and unequal K/V dimensions are rejected before physical TMH is selected. The implementation runs on both CUDA and ROCm through the server's backend interfaces, while the mixed physical operation itself remains a custom Triton path.

## 4.2 Pool layout

Every layer owns raw key and value tensors with shape

$$
[P_r,B,N,D],
$$

where $P_r$ is the raw-slot count. Warm keys retain the same logical vector length in INT8. Late-layer warm values are INT8. Early-layer values pack two 4-bit values in each byte, halving the last dimension. FP32 key and value scales have shape $[P_w,B,N]$.

Pool counts are solved together under the available KV budget. A binary search finds the greatest logical-block count for which all raw pools, layer-specific warm pools, scales, and descriptors fit. Solving for one logical capacity avoids independently rounded pools that cannot represent the advertised number of blocks.

The raw reserve includes room for one anchor per possible live sequence plus a configurable share for recent pages. Pool exhaustion raises an allocation error. No valid fallback moves a page between classes in the preserved implementation.

## 4.3 Descriptor format

Attention traverses request pages, not allocator free lists. For each request row and page position, the device tables provide a role and physical slot. A storage-kind field distinguishes canonical storage from a request-owned overlay. Canonical tables, indexed by logical block, hold the shared representation.

The attention tile size equals the cache block size. One program therefore loads one page descriptor and applies one representation path to every valid token in the tile. An earlier token-lane design repeated role and slot lookups. Page alignment removes that work and makes the metadata format match the allocator's natural unit.

Descriptor state is published through ordered scheduler events. The worker applies allocations and table changes before it launches the model step that uses them. For direct placement, the current cache update writes the payload named by the descriptor. For an already populated page, the event path can change metadata without copying data; Section 3.6 explains why that transition is not valid yet.

## 4.4 Cache update

The cache-update kernel runs one program per token and KV head. It converts the logical slot mapping into a request page, reads the page descriptor, and then chooses a raw, INT8, or packed-INT4 write.

Raw pages receive the input vectors in the native cache dtype. Warm keys and late-layer warm values use symmetric per-token, per-head INT8 quantization:

$$
s=\max\left(\frac{\max_i |x_i|}{127},10^{-6}\right),
$$

$$
q_i=\operatorname{clip}\left(\operatorname{round}(x_i/s),-128,127\right).
$$

The scale overhead is eight bytes per token and head—one FP32 word for keys and one for values. At $D=128$, the overhead is small enough that early warm K+V still occupies 200 bytes per token and head, compared with 512 bytes for BF16 raw K+V.

Decode normally takes the raw branch. Warm conversion occurs during direct prompt placement. A future implementation should split the common raw append from bulk page conversion; the current unified writer carries quantization branches that a single-token decode step does not need.

## 4.5 Correct INT4 contract and prototype defect

Early-layer values are intended to use affine four-bit quantization. The representable range must include zero before the scale is chosen. For a value vector $v$, define

$$
a=\min(0,\min_i v_i),\qquad b=\max(0,\max_i v_i),
$$

$$
s_v=\max\left(\frac{b-a}{15},10^{-6}\right),\qquad
z=\operatorname{clip}\left(\operatorname{round}(-a/s_v),0,15\right),
$$

$$
q_i=\operatorname{clip}\left(\operatorname{round}(v_i/s_v)+z,0,15\right),
\qquad \hat v_i=s_v(q_i-z).
$$

Including zero matters for sign-definite vectors. With the unexpanded interval $[v_{min},v_{max}]$, the vector $[1,2]$ produces a zero point clipped to zero and collapses both entries to the upper code; an all-negative interval fails symmetrically.

Because the zero point is embedded in the scale word, the writer must clear the scale's low four bits before calculating the final zero point and integer codes. In the equations above, $s_v$ denotes that recoverable, bit-masked scale. Otherwise the writer quantizes with one scale and the reader reconstructs with a slightly different one.

The evaluated kernel uses that unexpanded interval. Its INT4 path is therefore incorrect for all-positive and all-negative value vectors. The defect does not change payload size or the throughput cost measured later, but it invalidates any claim that the physical INT4 representation is numerically established. The corrected equations above describe the required format, not the code used for the preserved benchmark.

Two adjacent dimensions share one byte. Dimension $2j$ occupies the low nibble and dimension $2j+1$ occupies the high nibble:

$$
p_j=(q_{2j}\mathbin{\&}15)\;|\;((q_{2j+1}\mathbin{\&}15)\ll4).
$$

The implementation stores the four-bit zero point in the low four bits of the FP32 scale word. Packing clears those bits from the scale's IEEE-754 representation and inserts $z$; loading masks them out again. The convention saves a separate zero-point tensor at the cost of a small perturbation to the stored scale. Writer and reader must use the same masked scale convention, and any external implementation needs this bit-level definition.

## 4.6 Mixed-format attention

The attention kernel reads a page descriptor at the beginning of each KV tile. Raw tiles load BF16 keys and values. Warm tiles load integer payload and FP32 scales; early warm values are unpacked and shifted by their zero point. Reconstructed fragments are converted to the query dtype for dot products, while the streaming softmax state remains FP32.

For logits $x_j=q\cdot k_j/\sqrt D$, each tile updates a running maximum $m$, normalizer $l$, and weighted output $o$:

$$
m'=\max(m,m_t),
$$

$$
l'=e^{m-m'}l+\sum_j e^{x_j-m'},
$$

$$
o'=e^{m-m'}o+\sum_j e^{x_j-m'}v_j.
$$

The final output is $o/l$. Raw and reconstructed tiles share the same normalization, so a request does not need separate attention launches for each representation.

One kernel is convenient but expensive. The hot loop carries descriptor handling, role branches, scale loads, integer conversion, and packed-value logic even when a batch is mostly raw. The standard backend, by contrast, is optimized for one homogeneous format. TMH's performance gap is therefore not surprising; it measures the price of generality as much as the price of low-bit arithmetic.

Long decode can be divided into KV segments and reduced through partial softmax states. The preserved implementation enables segmentation only above 1,024 tokens because the extra launch and reduction work regressed the 1K regime. A raw-only path would be another natural member of the kernel family, but the evaluated runtime still sends raw pages through TMH's general physical interface.

## 4.7 Lifecycle accounting

Physical capacity depends on timely reclamation. Each representation has its own free list, and request-local overlays have a different owner from canonical prefix pages. The preserved implementation determines whether canonical storage remains live by scanning active descriptors. That choice is simple but expensive at concurrency because repeated cleanup can revisit a growing set of pages.

Reference counts keyed by canonical logical block would make release proportional to the number of changed references instead of the number of active descriptors. Later research notes report large gains from such a change, but the corresponding implementation revision is unavailable and those numbers are excluded from the main results.

## 4.8 Implementation boundary

The code path measured here can allocate final representations before prefill, write valid raw and warm pages, construct page descriptors, and execute mixed attention. It cannot yet make a populated page change representation. The INT4 writer also needs the zero-inclusive range correction described above.

Those two defects have different consequences. Missing migration limits which request histories are valid; the quantizer bug limits the numerical validity of early warm values even in direct placement. Capacity and performance remain measurable properties of the representation and code path, but physical quality does not. The evaluation keeps those categories separate.
