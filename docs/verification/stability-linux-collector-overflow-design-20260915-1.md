# Linux collector evidence-overflow audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. No packet or execution is released.

Collector bounds are: executable 1 MiB, manifest 4 MiB, request 65,537 bytes,
argv/env/stdout/stderr/events 65,536 bytes, setup 384 bytes and 512 owned records.
Retention records observed and stored counts plus truncation. Stream overflow maps
to `OUTPUT_LIMIT/EFBIG`; counter/hash overflow to `COLLECTOR_ERROR/EOVERFLOW`.
The `/proc/.../children` read is capped at 8,191 bytes and overflow maps to
`CLEANUP_ERROR/EFBIG`. Exceeding 512 owned records increments omissions and fails
the owner bound, so cleanup cannot be accepted. The outer supervisor separately
caps 512 descendant records and 1,536 events; omissions are counted, while the
collector oracle must still require zero omissions and complete cleanup.

The accepted 25-case packet already validates one-byte stdout loss with observed
65,537/stored 65,536, nonzero wait and cleanup. A future separate selector may
exercise more than 512 adopted descendants only under an independently reviewed
resource/cleanup packet. It must retain every partial artifact, raw wait and known
identity, fail with the exact owner-bound/cleanup status, and never claim PASS when
omissions are nonzero. Resource limits and identity-safe containment must be
reviewed before build; no application/production credit follows.

Reviewed hashes: collector
`09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f`,
supervisor
`cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7`,
accepted adverse build archive
`eaf0665189b49d80359b44109d7f015e19700112cc1d07d68b2d1ccd405e8675`.
