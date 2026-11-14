# M15-F01 exact-MM successor: source-only batch1

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This batch reuses the prior ihk_rust_scope candidate and gate implementation. The
predecessor source/profile/manifests remain copied under PREDECESSOR-* and the
original private/canonical evidence is unchanged. No compiler, test executable,
objtool, root, Docker, kernel module, guest or native workload was invoked here.
No canonical file or shared source was edited.

The substantive correction restores Linux's active non-lockdep write assertion.
The exact pin uses atomic_long_read(count)&1 and WARN_ON on every failure, even
with DEBUG_LOCK_ALLOC disabled. Rust now makes one aligned64-bit raw assembly
read before unlock's sequence-end and before VMA sequence/idempotence checks.
The new architecture warning leaf supplies Linux's resumable two-byte UD2 plus
relative verbose12-byte bug_entry(flags0x901), REACHABLE/special-data annotations,
SYM_FUNC_START/ENDBR and platform RET. It neither suppresses the warning nor
changes failure continuation. Its exact object/objtool acceptance remains open.

The existing three gate sites, outer+inner trace checks, seqcount begin/end order,
x86 compiler barriers, wrapping u32 arithmetic, single aligned VMA publication,
VMA rwsem sequence and current typed ownership/drop lifetimes are preserved.
Explicit assembly shared-word accesses avoid Rust references to concurrently
read sequence/count words; compiler clobbers are at least as strong as the pin.
Independent source/LKMM and actual generated-code review remain required.

The fixture now compiles15 byte-extracted original functions, including both real
rwsem assertion helpers. Only lower atomic read/warning emission is mocked.
Ordered assertion observations are compared in all22 valid vectors, including
idempotent VMA calls. Six isolated count vectors check writer/no-writer/high-bit/
negative bit patterns and repeated WARN_ON emission. Invalid operation schedules
remain rejected before FFI. Actual kernel UD2 is never invoked by the fixture.

The active source runner supports Python3.8, pins the real capture interpreter,
publishes argv before launch and preserves timeout/launch-error evidence. Body
and gate phases are separate. The pinned objtool requires GLIBC2.38, so the
host body profile excludes it. Gate/production ASM qualification belongs to the
reviewed compatible Rocky SDK/Kbuild lane. No fallback objtool, changed config,
manual production rustc or Linux/vendor C relocation is proposed.

production-source.patch contains the6-file private successor. It preserves the
reference C files, existing mcctrl_rust composite and cfg controls, recognizes
m15_fixture without enabling it and registers only the explicit kernel cfg names.
INTEGRATION-SOURCE.json names the hard-locked staging/audit source contracts
requiring root reconciliation; the6-file patch alone is not an executable staging
release. SDK-FOLLOWUP.json gives inert target/input mappings and required actual
readbacks. BODY-FIXTURE-PROFILE.json gives the exact next ordinary command.

Source identity/extraction/config checks, JSON decoding and Python3.8 AST parsing
are the only checks performed. Actual fixture, ABI/layout, codegen, objtool,
production link and matching native proof are all pending. This batch adds no
engineering percentage, C-retirement credit or whole-module acceptance.
