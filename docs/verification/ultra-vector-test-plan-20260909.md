# Vector instruction and FP state verification plan

Status: **planned; no new vector payload, instruction execution or guest PASS**.
The application catalog contains 56 vector cases: 55 real guest specifications
and one static executable audit. They bring the catalog to 273 logical cases;
parameter vectors do not increase that count. Packet 007 drafts three cases:
feature discovery, XMM preservation around raw syscalls and full YMM
preservation around raw syscalls. Luna or Spark can implement the packet after
the user chooses. Existing runtime gates remain mandatory.

## Machine and guest capability contract

The host inventory reported to this review is Intel Core i7-1065G7,
GenuineIntel, with SSE/SSE2/SSSE3/SSE4.1/SSE4.2, AVX, AVX2, FMA, F16C,
AVX-512 F/DQ/CD/BW/VL/IFMA/VBMI/VBMI2/VNNI/BITALG/VPOPCNTDQ,
AES/PCLMULQDQ/VAES/VPCLMULQDQ/GFNI/SHA. Preserve the exact captured host
inventory as descriptive evidence; it is not guest execution authorization.
No vector instructions are to be run on the physical host for this plan.

The historical QEMU TCG `max,la57=off` Linux guest reported an xstate mask
`0x21f`, containing x87/SSE/AVX, MPX and PKRU components. It lacks AVX-512
opmask and ZMM components. That historical observation is neither the current
Linux guest's nor McKernel's authoritative XCR0 value. Run the baseline-generic
discovery payload independently in both current guests before optional ISA
code, and retain their raw records even when their values differ.

The frozen feature table lives at `cases.json.vector_feature_contracts` and
is embedded transitively in each vector case's `payload_contract.vector_contract`.
The three-case context therefore needs no whole-catalog read. Record CPUID's
maximum basic leaf, leaf 1, supported leaf 7 subleaves and leaf `0xD` user-state
mask, component sizes and offsets. Read XCR0 with XGETBV(0) only when XSAVE
and OSXSAVE are set. Guard optional CPUID subleaf reads using their documented
enumeration rather than inventing results for unavailable leaves.

AVX requires leaf 1 ECX bits 26/27/28 and XCR0 bits 1/2 (`0x6`); AVX2 adds
leaf 7 subleaf 0 EBX bit 5. The CPU feature flag alone does not establish that
the OS manages the register state. [Intel optimization reference, AVX detection](https://cdrdv2-public.intel.com/821612/248966-Optimization-Reference-Manual-V1-050.pdf)

AVX-512 requires its individual leaf 7 feature bits plus XCR0 bits 1/2/5/6/7
(`0xe6`), with matching support in leaf `0xD`. Components 5/6/7 hold opmasks,
upper ZMM state and ZMM16–31. Check the separately enumerated component sizes
and offsets before observing or restoring state. [Intel ISA extensions reference](https://www.intel.com/content/dam/develop/external/us/en/documents/319433-024-697869.pdf)

The capability record contains raw leaves, guarded-XGETBV status/value,
derived predicates, exact image/module/ELF identities and QEMU CPU argv.
For each parameter, enable only the intersection of required features in both
engines. If a feature is absent, that parameter is BLOCKED, never a skipped
PASS. Do not sum partial passing parameters into a fully passing case. A
separate supported subset may be reported explicitly. Discovery itself can
pass its observation/derivation contract when optional features are absent.

Never run XSETBV, enable extra state, request AMX or change the QEMU CPU model
to make a case pass. New CPU configurations require separate reviewed input
manifests and complete current-pair regression evidence.

## Concrete coverage

| Cases | Technical assertions |
| --- | --- |
| Capability snapshot and negative predicate vectors | Actual raw feature records; synthetic missing-CPU, missing-OSXSAVE and missing-XCR0-bit vectors independently reject optional dispatch. |
| FXSAVE and standard XSAVE layout | Aligned guarded buffers; defined component bytes, sizes, offsets, initialized-state omissions and feature masks; no reserved-padding comparisons. |
| SSE2/SSSE3/SSE4.1/SSE4.2 | Integer lane arithmetic, PSHUFB zero/index semantics, selected lane blending and polynomial CRC32C. |
| AVX/AVX2 arithmetic and memory | Both YMM halves, wrap/saturation, cross-lane permutation, valid gather, page-straddling unaligned transfers and masked inaccessible lanes. |
| Floating-point arithmetic | Exact dyadic lanes, frozen reduction tree, explicitly bounded 2-ULP non-dyadic reduction, FMA one-rounding and F16C bit-level rounding. |
| Crypto extensions | Independent AES, carryless multiplication, VAES/VPCLMUL lane separation, GFNI matrix semantics and SHA256 known answers. |
| XMM/YMM/x87/MXCSR context | Real raw syscall windows; distinct owners across observed one-CPU thread switches; survivor state while another thread exits and is joined. |
| Local/nested signals | Explicit handler clobber followed by interrupted-state restoration, nested depth ordering, guarded alternate stack and upper-YMM checks. |
| New exec state | First-user-entry data/control snapshot before loader/libc FP use after a separately retired poison owner; default x87/MXCSR and zero XMM/YMM data. |
| Eleven conditional AVX-512 cases | Full-width integer/masked memory, k registers, all ZMM registers, EVEX shorter-width zeroing, VNNI, VBMI, IFMA52, bit population count, conflict masks and extended nested signal frames. |
| Static kernel opcode audit | Exact executable disassembly; unexpected vector/x87/MMX instructions fail outside individually reviewed FP management ranges. |

Each row above expands into the exact case objects, not an inferred set of
passing APIs. The 56 cases sample the reported machine's capabilities; they
do not claim exhaustive validation of every advertised instruction extension.

## Build and independent oracle rules

Use one generic dispatch translation unit or equivalent explicitly isolated
target functions. The baseline flags include `-march=x86-64 -mtune=generic
-mno-avx -mno-avx2 -mno-avx512f`; do not use `-march=native`. Optional vector
functions use a reviewed exact target attribute or assembly block entered only
after the runtime gate. Packet 007 can keep its assembly in each listed `.c`
file using explicit top-level assembly; it does not authorize extra shared
helpers or assembly files outside its six source/oracle paths.

Compile independent scalar references with `-fno-tree-vectorize
-fno-tree-slp-vectorize -ffp-contract=off -fno-fast-math`, and inspect their
actual emitted instructions. These flags alone are insufficient evidence.
No LTO/inlining may silently import optional instructions into the baseline
gate or replace the reference with the tested vector operation. Preserve
compiler version, full argv, dependencies, ELF hashes and complete disassembly.

For integer arithmetic, use unsigned modular arithmetic or explicitly widened
signed calculations; no undefined signed overflow. Every lane is checked,
including high halves, and distinct patterns rule out duplicated halves.
Inputs and expected byte arrays are frozen before execution. Checksums may
summarize output, but retain the original arrays for a mismatch.

Ordinary FP cases exclude NaNs, infinities and unreviewed exception behavior.
Exactly representable dyadic inputs use bit equality. The non-dyadic reduction
case fixes the operation tree and a maximum error of 2 ULP against a separately
reviewed high-precision oracle, with signed zero rules frozen. FMA is explicitly
single-rounding: `(1+2^-27)*(1-2^-27)-1` in binary64 must produce `-2^-54`;
separate rounded multiplication/addition produces positive zero under
nearest-even. Do not allow a tolerance to hide missing FMA semantics.

The F16C case freezes integer-derived binary16 encodings and flags for each
rounding mode. Denormal cases inspect MXCSR_MASK before enabling DAZ, mask
exceptions, freeze defined result/flag expectations and restore the original
environment. NaN payload propagation and unmasked SIGFPE require separate
future cases instead of broad allowed-result sets here.

AES uses fixed standard block/key vectors and an independently reviewed scalar
round oracle; SHA256 uses fixed digest vectors and scalar message scheduling.
Hardware and scalar paths cannot share the production instruction body as the
expected-value implementation. [NIST AES specification](https://csrc.nist.gov/pubs/fips/197/final),
[NIST Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final).

## Observe live registers without an ABI false positive

All state tests use an assembly **load → actual transition → immediate store**
window. A C function call may legally clobber caller-saved XMM/YMM registers;
their survival across `pthread_join`, `printf`, a libc syscall wrapper or a
compiler spill/reload does not test the kernel. Do not use a C array saved
before the transition as if it were a live register observation.

For the first packet, seed XMM0–15 or YMM0–15 with a deterministic per-register,
per-byte pattern, execute raw getpid/gettid/write/sched_yield as individual
parameter vectors, and store all bytes immediately. Inspect disassembly for
the complete window, register clobbers, stack addresses and branches. There
must be no call, compiler spill/restore or VZEROUPPER within it. Raw syscall
return and emitted write byte have independent expected values. Guest traces
must prove the intended local/delegated route rather than assuming it from
the syscall number. Validate register equality before emitting JSON.

Two to four threads on one McKernel CPU use raw futex handoffs with memory
ordering and monotonically checked owner/generation tokens. Require 64 actual
handoffs and prove another named TID ran between seed and snapshot; scheduling
yield by itself does not prove a switch. Each thread has a 256-KiB stack and a
distinct register/control pattern. The join case observes a surviving worker
across its own raw waits while another thread is joined, with ordinary join
semantics checked separately. It never requires registers to survive a C join.

Local signal cases issue an in-McKernel signal to the known current TID, hold
state in the raw assembly window and deliberately clobber it in the handler.
Nested handlers use distinct patterns and require depth `0,1,2,1,0`; the inner
return restores the outer handler, then outer return restores interrupted
code. Handler entry and recipient TID are retained. External Linux-to-McKernel
signal forwarding remains separately blocked by the missing native
SIG_THREAD/SEND_SIGNAL path; a local signal test must not imply it works.

First-entry tests remain behind `vector-first-entry-observer` and
`loader-extended`. Dynamic interpreters and pthread initialization may already
use vector registers. A reviewed minimal static ELF must snapshot at `_start`
before that code. A new thread may inherit its creator's state; do not assert
that every clone begins with zero registers. Prove a separate previous poison
owner has retired and a new exec identity reaches the observation point. x87
empty register payload bytes are not a defined zero-state oracle; compare
control/status/tag state. Missing trustworthy first-entry evidence is BLOCKED.

## State-size and kernel-code prerequisites

The selected source currently contains xstate initialization and initial image
construction in `arch/x86_64/kernel/cpu.c`, and signal save/checked restore in
`arch/x86_64/kernel/syscall.c` plus selected Rust/assembly bridges. Before any
new feature family is enabled, bind actual compiler inputs and review that
every initialization, allocation, clone, scheduler save/restore, signal copy
and teardown agrees on the enabled mask, alignment and checked size. Preserve
failed old attempts; this plan does not reinterpret them as fixed.

XSAVE buffers are 64-byte aligned and use the exact supported standard layout.
Reject a required size above the frozen per-case bound before issuing XSAVE;
the initial plan caps the application observation buffer at 16 KiB. Kernel
allocation bounds remain independent and must support the enabled mask.
Do not truncate a reported state size, assume a 512-byte legacy buffer or
compare init-omitted/reserved bytes as deterministic state. Snapshot defined
fields; never XRSTOR arbitrary synthetic user bytes as a discovery strategy.

Extended signal-frame acceptance is separate from an ordinary handler passing.
Its metadata, dynamic size and alternate-stack space require explicit review.
The Linux xstate documentation describes why larger enabled components change
signal-frame requirements. [Linux xstate documentation](https://www.kernel.org/doc/html/latest/arch/x86/xstate.html)
The AVX-512 nested-signal case stays blocked until that ABI contract passes.

The static audit must decode executable sections with a pinned instruction
disassembler, classify implicit-register x87/MMX/vector operations by opcode,
and retain symbol/address/source mappings. Grepping raw bytes or only explicit
register names misses instructions and creates false matches. Build a small
reviewed allowlist of exact state-save/restore/initialization instruction
ranges and bytes. A whole function name is not sufficient permission for
compiler-generated vector arithmetic. Existing no-SIMD checks on all three
native Linux modules remain unchanged and mandatory. The broader audit is
static evidence, never a guest execution count.

## Limits, evidence and execution sequence

All cases retain the established container limit of CPUs 2–5, 12 GiB, no swap,
512 tasks and no network. The Linux guest remains four vCPUs/8 GiB; McKernel
remains one CPU/128 MiB. Vector payloads allocate at most 2 MiB, use at most
four threads, finish within 10 seconds (20 seconds for transition/signal cases),
and have 15 seconds for cleanup. QEMU has an independent 300-second deadline.
No host instruction tests or host module loads are part of the plan.

First pass discovery and the unchanged current-pair baselines, then the packet
007 XMM/YMM windows, ordinary arithmetic, observed thread switches, local
signals, guarded memory and independent crypto vectors. First-entry state and
AVX-512 remain conditional late work. Every real case uses identical payload
bytes directly on pinned Linux guest and through the unchanged launcher.

Retain raw CPU records, evaluated masks, disassembly, input/expected/observed
arrays, raw wait status, exact source/ELF/DSO/module/image identity, command
argv, real McKernel OS/generation/PID/TID provenance, transition evidence,
resource cleanup and original failure/timeout captures. Mark missing feature,
missing oracle or missing provenance BLOCKED or FAIL as appropriate; it cannot
be normalized into PASS. All current oracle artifacts remain draft-unresolved.

On the first failure, stop the affected batch and preserve the original attempt
and kernel.log entry before diagnosis. A fresh attempt uses a fresh guest after
failure. The bounded one-candidate repair policy remains at most 15 minutes,
two files and 80 changed lines with independent review. FP/xstate ownership,
ABI, scheduler, unsafe memory or cross-thread contamination defects go to Max;
the executor must not invent a local register-reset workaround to make tests
pass. Changed kernel bytes invalidate previous binary coverage.
