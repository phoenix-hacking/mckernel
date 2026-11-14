Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Actual retained ordinary-readable feedback is sufficient for the first fix:
PID256 emitted exactly43B `FAIL stage=allowed-empty raw=0 unmap_raw=0\n`, normal
exit1/raw256, no stdout, both EOF and procfs_emptytrue. The source's first direct
get_mempolicy239(NULL,mask,256,0,MPOL_F_MEMS_ALLOWED4) returned0 and retained
guards, but every allowed-mask word was0. Baseline/process/mbind/interval tests
were never reached. The strict oracle/source remain unchanged.

ORDINARY-READABLE-FAILURE-FACTS.json binds full result.json and serial.log hashes,
an exact original ND_PAYLOAD line, decoded app stderr bytes and original PID256
cleanupACK0/procfs removal/retirement37errno0/process-release0 lines. The inner
runner reports wrong payload exit and reaped QEMU/capture_errors empty; its
application-executed acceptance flag staysfalse. Outer docker start --attach
rc1 propagates the failed inner diagnostic; it is not evidence of a host Docker
start/auth/policy rejection. No native acceptance or replay follows.

Only remaining minimum root observation: stable-FD atomic read of exact
root0700 t.owner-d7aa299c51544d4c932741c489adabe0/result.json, using the existing
failure-only program/caller and unchanged predicates. DATA changes only
STATUS/EVIDENCE/EXPECTED case constants, actual owner-status SHA and fresh
capture paths. MINIMUM-FAILURE-EXPORT-REVIEW-PAYLOAD.json contains the complete
exact argv/profile and current capture-context ref; root obtains one independent
failure-only read decision and fresh CPU6 grant, then invokes its callable_argv.

The atomic receipt must show actual absence_verifiedtrue/lease_retainedfalse
with exact source shape before positive runtime-retirement interpretation.
Missing/refused receipt preserves uncertainty; no automatic Docker/census/run/
cleanup follows. The source owner flushes it only after absence and lock release.
This is a receipt read, not independent physical/native acceptance.

No full guest TAR, owner TAR or three success-only readbacks are proposed.
No sudo, Docker, guest, app/compiler/stage/normalizer execution or cleanup ran
here; only ordinary reads of existing files and private source/DATA writes.
Family candidate1 remains failed and preserved. Root owns the functional
allowed-mask repair and subsequent review/release. Counts remain held; no speed
claim or metadata-only push prerequisite. Preserve UUID/noresize, scratch21,
mutex27:4, every failed byte and other workers' edits.
