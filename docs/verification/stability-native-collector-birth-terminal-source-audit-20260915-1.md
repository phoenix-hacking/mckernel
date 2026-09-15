# Native collector birth/terminal producer audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. This is a bounded read-only M02-C audit. It
does not freeze an ABI, authorize implementation, or establish native collection.

`kernel/include/process.h` (SHA256
`907391bd99a38b48be54ff6700f1ca12143e5a9bfabf4826b6f09ab2b842bc6c`)
stores only numeric TID plus thread pointer in `mcexec_tid`; the process TID array
is a reusable slot array/count, not a lifetime inventory. `struct thread` has a
numeric TID, process pointer, status and exit status but no birth generation.
`kernel/syscall.c` (SHA256
`ac80bb17e41979652e3dd90f8a94d205c28853cd6171975fcf4349f3d301ab58`)
reuses the first free proxy-TID slot. `terminate()` writes group/thread terminal
status and process exited state before the later `finalize_process()` and
`release_thread()` path; there is no native publication hook or terminal serial.

The retained host `Process` already combines OS slot/generation with Linux
`ProcessId` object identity, so it protects Linux numeric-PID reuse. It does not
provide a McKernel guest-thread birth identity. The existing versioned application
ABI has PREPARE/START and WAIT/COPIED/RETURN delivery records with a per-delivery
64-bit serial, but its 64-record trace is diagnostic and cannot prove a complete,
lossless birth/terminal ledger.

A future reviewed producer record would need fixed-width fields for version,
event kind (`BIRTH`, `TERMINAL`, or `RETIRE`), OS slot/generation, application
token, guest process and thread IDs, guest-thread generation, terminal status and
signal, monotonic sequence and timestamp. Generation allocation must occur under
thread/process serialization at creation. Terminal publication belongs immediately
after the authoritative status writes; retirement must be a distinct later record
at final release. This is a proposal only.

Loader/transient-map completeness, birth-ledger completeness, a source-bound
terminal hook, unchanged-`mcexec` stream attribution/no-loss, and cross-clock
guarantees remain unresolved. A native-acceptance ABI cannot be frozen without
the loader and stream contracts; only further structural drafting is ready.

Reviewed host identities remain those in the prior ABI review: `mcctrl_process.rs`
`392391cc1db8eaf8d26283ca77a7d69150a0bbf026dfd01120970d7fd601a925`,
`application_rpc.rs`
`9f811c86c4e996294a6cd3be6b83315dabd20a3fb375419e091f4b9dedcfad39`,
`application_syscall.rs`
`a1f5e98413a83f7c11c069d23d883379aa64578b55e011dff49c528a236321fd`,
`smp_application_syscall.rs`
`4118de1401f33b2df17393660e6acbce2f337dca8a9cdfcf10965b1d3dc84c55`,
and `smp_procfs.rs`
`7aba4319fdc6fa76761ca01128c7a7d920c4be85244737167122c914fc1268d5`.

No implementation, build, guest execution, application acceptance or production
gate credit follows.
