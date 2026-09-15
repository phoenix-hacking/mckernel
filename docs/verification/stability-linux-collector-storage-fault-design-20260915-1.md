# Linux collector storage-fault design — 2026-09-15

Status: **PASS_DESIGN_ONLY** for a new additive `storage-fault-v1` packet. No
source/build/execution release follows.

Pin collector SHA256
`09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f`.
The report path can return false on open/stream/final-sync failure without calling
the ordinary failure recorder; a complete report may therefore say `COMPLETED`
while raw collector exit is 125 (raw 32000). Every such case needs an independent,
precreated, externally fsynced witness and must preserve the original report.
There is no production truncate call; `sink.truncated` means retention-limit
overflow. Truncation belongs only in a derivative-corruption oracle negative.

Separately guarded generated collectors should inject one exact occurrence of:
attempt mkdir/open/parent-fsync EIO; artifact create ENOSPC; input open EIO; real
seven-byte write then ENOSPC; zero-byte write; one EINTR or positive short writes
followed by success; live-child stdout prefix then ENOSPC; artifact fsync EIO after
cleanup; report open ENOSPC/fdopen ENOMEM/partial stream/final fsync; final directory
fsync; and an earlier request-write failure followed by sync/report failure.
Unselected calls remain real. This explicit simulated-I/O authorization is local
to the new packet and cannot weaken adverse-v1.

Require exact raw 256 for retained collector failures and raw 32000 when reporting
itself fails; preserve prefix sizes/hashes, child wait (including SIGKILL when
needed), EOF/reap/cleanup, immutable first failure and additive secondary errors.
Pre-child cases must not invent cleanup completion. The independent witness binds
nonce, source/ELF, argv/environment, collector PID/startticks, seam/occurrence,
errno, operation boundary and monotonic time, with checked file and parent-dir
fsync. Witness failure invalidates the case.

New files only under `linux-sealed-v1/storage-fault-v1/` plus one focused test.
Require strict source/oracle review, compiler/dependency/ELF binding, and separately
reviewed root execution. Eventual scope is
`PASS_INSTRUMENTED_STORAGE_PATH_ONLY`, never media/power-loss durability,
McKernel/application or production-equivalence credit.
