# Appendix A. Physical Contract and Capacity Derivation

## A.1 Page descriptor

The logical block table remains the scheduler's source of identity. TMH adds the following physical information for each request page and layer.

| Field | Meaning | Consumer |
|---|---|---|
| logical block | scheduler-visible page identity | prefix cache, block manager |
| role | raw anchor, raw tail, early warm, or late warm | cache update, attention |
| physical slot | index within the selected pool | cache update, attention |
| storage kind | canonical or request-local overlay | resolution and cleanup |
| request row | active-batch descriptor row | worker and kernel metadata |

Canonical role and slot tables are indexed by logical block. Request tables contain the resolved view needed by the current batch. A private request usually points to canonical storage. An overlay changes only the request-level storage kind and slot.

The descriptor is page-grained because the kernel tile is page-grained. Token offsets are derived from the position inside the page and do not carry a separate representation tag.

## A.2 Role construction

For a sequence of $P$ pages and a configured tail of $h$ non-anchor pages, the raw region is

$$
\{0\}\cup\{\max(1,P-h),\ldots,P-1\}.
$$

Page zero receives `PINNED_RAW`; the trailing interval receives `HOT_RAW`. Pages between them form the old body. At layer $l$, an old page receives

$$
r(l)=
\begin{cases}
\texttt{WARM\_INT8\_INT4}, & l<\lfloor2L/3\rfloor,\\
\texttt{WARM\_INT8\_INT8}, & l\ge\lfloor2L/3\rfloor.
\end{cases}
$$

When the anchor and tail overlap, the page remains pinned. A sequence shorter than the raw interval has no warm body and gains no payload capacity from TMH.

## A.3 Scale-aware page sizes

For page size $B$, KV-head count $N$, head dimension $D$, and two-byte BF16 raw storage:

| Representation | Bytes per layer-page |
|---|---:|
| raw BF16 K+V | $4BND$ |
| early warm K8/V4 | $BN(D+\lceil D/2\rceil+8)$ |
| late warm K8/V8 | $BN(2D+8)$ |

The eight-byte warm overhead comprises one FP32 key scale and one FP32 value scale for every token and KV head. The early value zero point is encoded inside the low four bits of the value-scale word and does not allocate another tensor.

For $B=16$, $N=4$, and $D=128$:

| Representation | Payload | Scales | Total |
|---|---:|---:|---:|
| raw BF16 | 32,768 | 0 | 32,768 |
| early warm | 12,288 | 512 | 12,800 |
| late warm | 16,384 | 512 | 16,896 |

The 32/16 early-to-late split gives

$$
\bar W=\frac{32(12800)+16(16896)}{48}=14165.33\ \text{bytes}.
$$

With a 25% raw reserve and eight descriptor bytes per logical layer-page,

$$
C=0.25(32768)+0.75(14165.33)+8=18824,
$$

and

$$
\frac{32768}{18824}=1.74076.
$$

The continuous model thus predicts about 74.1% more logical pages. Finite allocation records 73.82% after anchor reserve and integral pool rounding.

## A.4 Old-body denominator

The same-hot INT8 baseline assigns one byte to every old key and value element, for $2H$ bytes per token and head. When exactly two thirds of layers use K8/V4 and one third use K8/V8, TMH uses

$$
\frac23(H+H/2)+\frac13(H+H)=\frac{5H}{3}.
$$

The saving is

$$
1-\frac{5H/3}{2H}=\frac16=16.667\%.
$$

This calculation omits scales on both sides and applies only to the old body. It should never be substituted for the physical capacity multiplier.

## A.5 Packed INT4 encoding

The corrected value range is $[a,b]$ with $a=\min(0,v_{min})$ and $b=\max(0,v_{max})$. The four-bit zero point $z$ occupies bits 0–3 of the FP32 scale word:

$$
u_{stored}=(u_s\mathbin{\&}\mathtt{0xfffffff0})\;|\;(z\mathbin{\&}15),
$$

where $u_s$ is the IEEE-754 bit pattern of the scale. The bit-masked scale recovered from $u_{stored}$ must also be the scale used to calculate the final zero point and integer codes. The reader obtains

$$
z=u_{stored}\mathbin{\&}15,
\qquad
u_s=u_{stored}\mathbin{\&}\mathtt{0xfffffff0}.
$$

For packed payload byte $p_j$, dimension $2j$ is $p_j\mathbin{\&}15$ and dimension $2j+1$ is $(p_j\gg4)\mathbin{\&}15$. The evaluated head dimension is even; odd dimensions would require an explicit padding convention.

## A.6 Transactional migration

A descriptor for an existing page is valid only after its destination contains every token named by the logical page. A complete state machine therefore has four states:

$$
\text{allocated}\rightarrow\text{materialized}\rightarrow\text{published}\rightarrow\text{retired}.
$$

The materialization step may copy raw data, quantize raw data, or dequantize a warm page into an overlay. Publication changes reader-visible metadata. Retirement releases the old slot only after outstanding readers finish. The prototype implements allocation and publication but not materialization for live transitions.
