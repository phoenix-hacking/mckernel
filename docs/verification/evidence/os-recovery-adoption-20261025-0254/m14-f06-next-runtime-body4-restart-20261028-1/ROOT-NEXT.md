Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The next distinct F06 candidate is `arch_ptrace_xstate_copy_from_bridge`. The
retained accepted CURRENT116 arch77db1a40 object defines it as GLOBAL FUNC40bytes
at0x2f0 among17 selected functions. The complete selected body still exists in
the captured actual canonical source and has no existing Rust public provider.
Do not duplicate banked117/vDSO-info,118/restore-FP, or sealed body3/xstate-copy-to.
This source work touches no signal-dispatch candidate, undefined-domain hold,
credential or service hold. The retained object is evidence of selection and
does not supply fresh runtime/host ownership clearance.

The Rust provider owns the original entire callback: read the real borrowed
`Thread.fp_regs` pointer; return-ENOMEM on null without copying; otherwise call
the already selected Rust `x86_memory_helpers::copy_from_user` with that exact
FP pointer as destination, the original user address as source and unmodified
size_t count. Preserve the genuine signed-int32 copy result by signed-long64
widening, including positive values, negative values and partial-write effects.
No target lookup, allocator, mapping, lock/ref acquisition/release, FP instruction,
count/address normalization, local validator or error translation is introduced.

The original caller retains a live/aligned target Thread, readable FP pointer
field, writable/live target FP allocation and its original ptrace/thread write
exclusion. No Rust reference is formed over the borrowed Thread, FP state or user
memory. Null/invalid thread addresses are outside the original C defined domain
and are excluded from this fixture. The nonvolatile field read assumes the same
caller exclusion as C; no concurrent-mutation policy is added. Existing
`ptrace_write_regset` and its NT_X86_XSTATE clamp remain unchanged.

`PINNED-PREIMAGES.json` captures the four actual canonical preimages once. They
were still adopted116 at capture: arch8d24cb88/CMake9650cc9f/lib6dc007c9/ABIff48bc2e.
The source generator reuses those snapshots and never refreshes them. The
source checker reports current canonical drift separately. Root's imminent118
adoption requires a coordinated rebase/explicit current dependency bindings
before any grant if it changes these paths; these patches do not claim118
preimages. Do not overwrite sealed body3 source/grant/HOST evidence to compose.

The private Rust module, arch selector, crate-module selector and CMake proposal
use `f06_ptrace_xstate_copy_from_candidate` plus paired
`MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_FROM`. CMake adds them only in the existing
supported x86/Linux6.12/non-UBSAN branch. The fallback retains the exact original
C bytes. Root must merge the disjoint hunk into its actual adopted source, copy
the candidate module to the named production path and rebind the genuine
origin/profile after all edits. No prior origin receipt, prefix or nonce is reused.

The future real-header witness checks the actual nominal copy-from-user/public
bridge signatures, LP64/int32/ENOMEM, typed borrowed target field and actual
Thread/xsave size/alignment/offset. The complete Rust ABI file is snapshotted
unchanged, avoiding a second modeled Thread. The C oracle includes the genuine
headers and unmodified original body; names alone redirect its user-copy effect.
The Rust fixture includes the entire production module unchanged and mocks only
the preexisting Rust copy-from-user provider.

The prepared1944 pairs vary null/nonnull FP storage, zero/normal/boundary/high-bit
counts, signed-int32 result extrema, actual/null/high-bit user sources and four
partial-write prefixes. They compare exact return/provider call count and raw
argument/result trace, every4096 destination/source byte and every5568 Thread
byte. A separate expected-result/effect/full-canary calculation checks partial
writes only affect FP storage, preserve source bytes/Thread metadata, and make no
copy on null FP state. Null/high-bit user and huge counts are mocked forwarding
checks only; they do not claim real ptrace/usercopy acceptance. Null thread is
never run. No real usercopy, target memory, hardware, module or native effect runs.

`FUTURE-HOST-COMMANDS.NOT-GRANTED.json` binds four proposed commands. The smallest
next command, after Root's current-source rebase/admission and fresh ordinary
grant, is command0: compile the genuine-header ABI witness. Then compile the
unchanged-C oracle, compile the exact-module/actualABI Rust fixture and run the
single1944-pair test. Root owns output creation and CPU/resource/account/window/
identity admission. No compiler or fixture ran for body4; only pure Python source,
preimage and exact-patch checks on CPU7/jobs1 ran. Body3's prior1944pairs never
count as proof for this new write callback.

Production closure remains fullcrate, selected/fallback full arch TU and actual
default link with exact new origin/profile. Require target absent from selected
C FUNC definitions and present once as a Rust provider resolving the unchanged
write-regset caller, with the same existing Rust copy_from_user and preserved
unrelated callback/data/389 registry records. Matching-current native write-regset,
partial-error and target lifetime checks are separate obligations. Predicted C
function removal is1; actual default/native/file deltas are0. CURRENT116/C71/Rust68,
M14files4/6, M15files1/8 and35/35 remain unchanged. Only this new private sibling
was written; all earlier failures, controls, exclusions, scratch21 and permanent27:4
remain intact. No whole-file or percentage credit is claimed.
