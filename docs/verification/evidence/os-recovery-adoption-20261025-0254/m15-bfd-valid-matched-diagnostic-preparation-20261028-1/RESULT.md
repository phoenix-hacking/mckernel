Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The nearest genuine valid diagnostic is a new disposable idle OS using the
retained CURRENT110 kernel `60e62f97` and exact existing module/boot/base-capsule
tuple, followed by paired original-C-BFD/reference and current mcinspect `--ps`.
The kernel has actual `.symtab`, `.debug_info`, `.debug_abbrev` and `.debug_str`
sections and the required clv/mck_num_processors providers. These facts were
read with the existing ELF parser; no diagnostic binary or external ELF tool ran.
This tuple can qualify the new tool against CURRENT110. It cannot provide
matching CURRENT116 native credit.

`BOUND-INPUTS-AND-CONTEXT.json` binds the accepted current mcinspect `dcd94257`,
eclair `ea39080e`, kernel and retained SDK21 original-C-BFD reference executables
`0b753618`/`7e277510`. Each exact byte hash matches. The reference executables
retain the same accepted Rust frontend/vendor objects and replace only the BFD
bridges with their original C bodies; they are not full-C frontend builds.
The original retained C frontend supplies the separate PS formatting and thread
state oracle in `ORIGINAL-C-AND-REFERENCE-ORACLE.json`.

There is a concrete loader dependency blocker: both mcinspect executables require
`libelf.so.1`, which is absent from the retained native capsule final map and the
two corresponding paths in its known retained root. libc and zlib are present.
The plan supplies an exact, UNGRANTED `docker cp -L` argv to obtain that real
library from the still-owned immutable-SDK BFD container, plus an alternative
using the existing reviewed immutable-image extraction profile if that container
has already retired. Root must bind its actual bytes, symbol versions and
recursive dependencies. No host library substitution or Docker command ran.

The private Rust collector successor reuses the existing module load, native
boot, child supervision, kernel-log capture and bounded guest shutdown path. It
replaces the original235 application/retirement sequence with reference/current
valid idle probes and checks the empty user namespace before/between/after them.
Original235 and original227 sources, payloads, manifests, nonces and archives are
untouched and are not replayed. Complete streams/statuses have distinct
M15_BFD_PROBE markers; the final result has its own case prefix.

One bounded source correction handles a real original-C behavior: the DWARF
walker can print ordinary declaration/no-location continuations before reaching
the real variable definition. The oracle parses that exact C trace grammar,
requires both variables to resolve, then requires the exact PS header and one
active CPU0 idle row with TID0/PID0/stateR and a nonnull kernel pointer. Complete
streams must also match the retained reference. Help, stripped/missing inputs,
empty/header-only results, unresolved globals and identical wrong rows fail.
The new diagnostic profile retains up to64KiB per stream; all supervisor
ownership/deadline bodies remain exact. Complete probe bytes are serialized once,
with a final<=4096-byte summary. Root must qualify the existing owner's complete
1MiB serial budget; this proposal grants no budget increase. Original app
protocols retain their existing1KiB bounds. Original proposal bytes and prior
pure-check captures are retained beside the corrected sources.

`native_diagnostic_overlay_bfd.py` is a private fixed-input extension of the
existing stable-FD overlay. It adds only current mcinspect, the retained reference
and genuine libelf, each with a required actual hash; the original matching base,
kernel/modules, inactive app and mcexec bytes are preserved. No capsule has been
composed. The new collector has not been Rust-compiled or executed. The exact
next HOST compile argv, dependency-export argv and valid runtime argv are in
`VALID-MATCHED-DIAGNOSTIC-PLAN.json`.

Eclair remains a separate valid-context step. No genuine offline mcdump is bound.
Its nearest live case requires a pinned GDB/recursive runtime closure, finite
prompt interaction and separate DUMP_NMI/paused-state teardown review. Its C
oracle expects one idle debugger thread, remote ID2000000000/hex77359400, and
`PID 1, idle running on CPU 0`; that PID is the original debugger's idle sentinel,
not a user process. Probe exit never proves OS resume or public resource
restoration. No unbounded expect script is released.

Six pure test methods passed on CPU6/jobs1: four positive groups and31 negative
controls, including declaration traces exceeding the old1KiB app bound and the
fixed capture ceiling. Final captured wall time was0.062495s. Tests use synthetic
capture/archive data and do not count as valid diagnostics. Actual tool,
collector, compiler, guest, stage, Docker, root, query and guard runs are all0;
native/file-closure deltas remain0. BFD consumed noncefaac/container2460 remain
retained ownership facts; no physical clearance is supplied here.

Root's next independent steps are the exact new collector HOST compile and real
libelf binding, then actual stage/decoder/owner review and a fresh admitted idle
native case after current-free acceptance. Current-context receipt, new nonce,
stage hashes and native execution release remain genuinely unbound. The same
immutable time/credit limits and all exclusions continue to apply.
