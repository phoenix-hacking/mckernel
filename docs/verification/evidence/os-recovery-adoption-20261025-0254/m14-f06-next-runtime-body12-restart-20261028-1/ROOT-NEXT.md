Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

BODY12 ports the actually selected255-byte arch_vdso_map_log_bridge into Rust.
Exact ABI: int32 event/error/pages; ProcessVm*; four unsigned long64 arguments;
void result. Actual ProcessVm.proc offset136 holds Process*, whose int32 pid is
at456. For mapped event3, null VM or null proc prints-1. Valid objects retain
their original caller-owned lifetimes/exclusion. No reference/hold/release/lock,
allocation, new error or changed error propagation is introduced. Other events
never access VM. Unknown events produce no output. All formats retain exact
typed int/unsigned-long varargs, including lower-case %lx and ignored print result.

Mapped output reuses the existing arch_vdso_state_bridge to obtain the same stable
image-lifetime signed ptrdiff_t offset address, then performs the same plain read
and modulo2^64 unsigned-long conversion. The provider only publishes optional
borrowed addresses. Actual canonical C provider or banked BODY6 Rust provider has
this exact contract; no new provider/storage owner is added. HOST links the
byte-identical BODY6 helper and BODY7 real Rust storage, independently qualified
earlier. These frozen copies are fixture dependencies and must NOT be adopted as
duplicate new modules. Production reuses the existing/banked providers.

New logger owns one32B/align8 Rust __verbose descriptor directly, reusing actual
Ddebug and kprintf. Filename comes from existing genuine F06 origin producer;
function arch_vdso_map_log_bridge/nullfmt/line3084/flags0/padding0 match the389-row
CURRENT116 registry. Original CURRENT116 function text is verbatim identical to
canonical118. Canonical118 and frozen cumulative source currently resolve this
site to3086, a preexisting two-line source-only drift. This target's fallback uses
#line3077 to preserve its accepted3084 identity; after-function/outer-exit numeric
restores retain unrelated canonical118 logical positions. Record all this in
ORIGINAL-DESCRIPTOR-IDENTITY.json; do not reset or edit frozen cumulative evidence.

Selection patch, Rust module and CMake proposal are based on exact canonical118,
with MCKERNEL_RUST_F06_VDSO_MAP_LOG/f06_vdso_map_log_candidate. Selected C has only
the original ABI declaration; no new C compute implementation or descriptor.
Flag-off keeps the original C function/macro/static descriptor. Root composes this
disjoint patch with frozen BODY3-9 and BODY10/11; no canonical/shared writes here.
Keep all existing selectors, one offset owner and one debug record per original
identity. Recompute exact source/argv/profile/origin refs through existing tools.

Nearest check is the four exact ordinary HOST commands in FUTURE-HOST-COMMANDS:
real Rust logger/descriptor/state/storage object; genuine-header original C oracle
and extern-only consumer partial link; Rust fixture compile; one fixture run.
Original C function identifier remains unchanged using only an asm ELF alias, so
__func__ is authentic. HOST-only #line restores original filename/line. Original
C oracle owns its own independent static offset and LOCAL debug record. Selected
Rust owns the counterpart offset and GLOBAL debug record. Exactly two HOST debug
records are intentional; production requires one original identity. All output
and descriptor/object mutation use own HOST mock storage, with no real mapping,
VM/provider/kernel/hardware/usercopy/ptrace/native effects.

Fixture covers56250 event/flags/error/signedPID/signedoffset/nullVM/nullproc/pages/
printer-result cases with five routed unsigned-long boundary patterns, plus7
ignored-VM cases. Compare unchanged C oracle AND independent exact typed arguments,
format/render/canaries, inherited metadata/byte27 flags, complete Process/VM bytes
and offset state. Genuine C assertions prove actual type sizes/alignment/offsets;
real ELF must prove one32B writable __verbose Rust target, C imports only, one
selected logger, no constructor and unique partial/final symbols.

After HOST, smallest next artifact checks are genuine selected/fallback C TUs,
full Rust crate/default link and389-record multiset, then matching-current native
ordinary map diagnostics/configuration proof. Source/HOST gives no default,
native, data-retirement or file credit. Actual CURRENT116 remains archC17/C71/
Rust68/M14files4/6; after all queued bodies3-12, five selected Cfunctions remain:
arch_ptrace_regset_log_bridge (%x/long defined-domain contract unresolved), held
arch_rt_sigreturn_xrstor_bridge/arch_native_signal_bad_frame_bridge/
arch_rt_sigreturn_context_bridge and do_signal. No held path is entered.

BFD retirement/current-free/Root63 completed21:50 and is historical accepted
freee13/ledger6b/bindingsbe0; never replay. New pending boundary is failed-unlaunched
A2 custody supplement/A3 narrow source fix. Model/native clearances remain
separate. Same06:00Z deadline, cumulative credit, dirty evidence, failures,
scratch21/permanent27:4/exclusions/controls remain preserved.
