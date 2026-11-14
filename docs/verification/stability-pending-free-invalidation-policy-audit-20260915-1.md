# Pending-free invalidation/backing policy audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. No source integration is authorized.

Corrected private `mem_helpers.rs` SHA256 is
`647825d8c51a9f584d1229a2389fbb81105e4bbf94bfcf95a12d172c5dde112b`.
Its drain sets `PM_NONE`, poisons/removes the descriptor, then invokes a void
`free_fn`; a clear/invalidation failure cannot be propagated or retried. Legacy C
has the same release-before-outcome behavior. Native page zeroing detaches the
chain and publishes zeroed chunks without a clear acknowledgement. The existing
host-PTE clear forwards munmap and some callers discard its result.

A future policy must retain descriptor/backing ownership and `PM_PENDING_FREE`
until successful clear plus TLB acknowledgement. Transient failure must requeue an
unchanged batch with bounded retry/backoff. Terminal or unknown failure must
quarantine it, preserve mappings/backing, emit durable typed error/identity and
abort the owner path. Failed or unknown clear must never make pages reusable.

Source hashes: `page_alloc.rs`
`3e89740f0215d46d83d731fe9338ae70792e2cb2b4cbdafd416dc5d1bb6200fd`,
`kernel/syscall.c`
`ac80bb17e41979652e3dd90f8a94d205c28853cd6171975fcf4349f3d301ab58`,
and `zero_pages.rs`
`47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def`.
The original audit response accidentally repeated the page-allocator hash for
`mem_helpers.rs`; this record corrects it using the exact reviewed candidate and
attempt-3 archive. No error-returning acknowledgement/backing-reference contract
exists, so no runtime/application/production credit follows.
