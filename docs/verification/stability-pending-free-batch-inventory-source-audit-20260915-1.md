# Pending-free bounded-inventory source audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. No implementation or integration is authorized.

The dirty candidate `kernel/rust/mem_helpers.rs` (SHA256
`3bdb98c725f56795d8aa05273db9bd68a15aae3efb5b205836c6c995f73b02ca`)
validates a complete intrusive ring with cycle detection but has no independently
trusted node-count bound. It dereferences `next`/`prev` before such a bound, and
the later drain traverses to the sentinel. The legacy C finish loop is likewise
unbounded. `kernel/mem.c` SHA256 is
`167ad2b976bcdec048a625dedf68a9b7c1ef6db7c57f3ceddf3582d54887101a`.

The page descriptor supplies list links, mode, physical address and `offset` as
page count. Enqueue currently accepts any page count and derives a descriptor
through `phys_to_page`; aggregate memory-chunk/page totals and allocator ranges do
not independently prove descriptor cardinality or ownership for a corrupted ring.

A future contract needs a producer-maintained trusted descriptor count/capacity
captured at begin. Validation must reject before callbacks or mutation when the
count is exhausted or mismatched, a node repeats or is foreign, a sentinel is
malformed, page count is nonpositive/overflowing, or physical range/alignment and
membership fail. Each node must be proven safe before dereference. Null/one-sided
heads, dangling links, foreign cycles and non-pending mode remain required
negatives.

No trusted inventory count/capacity or page-range ownership API is wired into the
present ABI. Production source integration remains blocked. No runtime,
application acceptance or production credit follows.
