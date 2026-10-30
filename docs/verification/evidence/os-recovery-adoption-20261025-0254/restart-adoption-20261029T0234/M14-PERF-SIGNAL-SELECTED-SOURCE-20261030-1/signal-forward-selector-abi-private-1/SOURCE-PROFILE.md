# Signal-forwarding paired selector and ABI inputs

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only descriptor. Existing Rust bodies and CMake/C selectors are
reused without editing them. This is not independent acceptance, an executable
profile, a native release, a C retirement or an M14 file closure.

## Existing artifacts and baseline

* Retained `M14-REMAINING23-D-1/defined-callers-correction-1/SIGNAL-DEFINED-CALLERS.ON-FIRST20.PRIVATE-NOT-APPLIED.patch`: SHA-256
  `13d4813e5c8be05a33908e8c252f22bb7596e43ae55bf9390817feb3af118b2f`.
* Its existing `postimage/kernel/rust/f03_signal_forward_defined_candidate.rs`:
  SHA-256 `fa55a0ca4436c8b330221865db8ebe0a8481886a88a4212c817a197199b0c392`.
* Patch preimages: `kernel/syscall.c` SHA-256
  `3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3`,
  `kernel/rust/syscall_policy.rs` SHA-256
  `14881100a803a90b25950b0c56d6fff6642a4cc8614c895a87418c6b7540dc50`,
  `kernel/CMakeLists.txt` SHA-256
  `30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd`.
* Historical qualified 19-definition generic C object is
  `0633c5248eb68a59c1920799ad1ef1040e27f8733b074fbeea1fc58289eb398c`;
  image `1cd7e4e66bdbd7d34bcca2e7cb698da814df470ffd726270a612a2d92faf8c38`.
  Its artifact cursor records both C names as present; no new candidate image is
  implied. Its accepted producer profile SHA-256
  `8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d`.
* Named Root source contract `ROOT-CONTRACTS.APPROVED.json` SHA-256
  `534c4df211bcf940f19191607d8d3d26d426e2f82d3bfaa7f392c41fe06df19e`;
  independent source contract review SHA-256
  `776d9ce095932811212c2e80bb46af195bc067a3d3d7821ada79593885c0f9d0`.
  These approvals define unused transmitted fields; they grant no build/native
  authority and do not claim parity for the old uninitialized fields.

The patch is based on the same C/Rust/CMake preimages as the qualified source
packet; other independent compositors may append changes to the same Rust and
CMake contexts. The compositor must integrate once, verify exact successor source
hashes and preserve all other writers. Do not apply this historical patch blindly
across changed contexts or duplicate the Rust bodies.

## Narrow source contract and caller ownership

The x86 mask bridge writes raw context argument fields
`[sigmask,0,0,0,0,0]` and calls the existing generic forwarding entry with 14.
The action bridge writes `[signed_sig_as_unsigned_long,handler,flags,0,0,0]`,
then calls it with 13. It reads handler after arg0 and flags after arg1; its
borrowed `KSigAction` remains live and aligned through those reads. The temporary
context is raw `MaybeUninit`, and only the six initialized argument fields may
be read by the generic forwarder; no whole initialized context is claimed.
The selected x86 getter source reads those six scalar fields and generic
forwarding builds its own request before the synchronous `do_syscall` call.
Runtime request/response lifetime, cancellation and final linked implementation
still require proof; this source observation does not discharge those checks.

`rt_sigprocmask_body_result` validates/copies, updates the guest mask, calls the
bridge, ignores its return and returns the existing guest result. The selected
`do_sigaction_body_result` validates, copies under the writer lock, unlocks,
then forwards only a non-null action and ignores bridge return; its caller keeps
the action storage live synchronously. Each bridge itself returns the unchanged
generic-forwarding result. The current Rust executor custom mask consumer reads
arg0; the action consumer reads arg0/arg1, ignoring flags while the bridge still
preserves original arg2. These are project wire payloads, not Linux syscall
argument shapes. Review actual linked executor consumer and uncertain cancellation
outcomes separately. Source hashes for current inspected x86 getter helper,
Rust ABI and executor helper are respectively
`8db479fbea9493ee498bf5d78aef71589b49d9f065e13a8617b5765cd681c194`,
`ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e`,
`d786abc498f5951c65b28246071fcbbe8023392f2cf7a372902fa76b259ed73d`;
they are inspected working-tree inputs, not asserted to match a later image.

## Paired selection and real ABI data

The existing default-off CMake option `MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL`
selects C `MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL` and Rust
`f03_signal_forward_defined_candidate` only in its x86_64, non-UBSAN path.
The action C bridge lies under `MCKERNEL_RUST_SYSCALL_POLICY_HELPERS`; the mask
bridge is outside that condition. For this descriptor the matched policy-helper
configuration is required. The retained producer C argv includes the policy
macro, Rust argv selects its syscall entry, and neither contains the signal
candidate selector. Separately recorded raw C and Rust commands must add both
candidate selectors in one coherent build; the source macros do not themselves
prove matching cross-language selection. Establish exact ENABLE/architecture,
policy, CMake options, emitted argv, C and Rust symbol uniqueness and all four
ON/OFF/mismatch outcomes through the eventual reviewed build/link oracle.

For real-header ABI comparison, use the exact selected C translation unit,
headers, generated config, SDK21, compiler and flag set; obtain independent
numeric C and Rust object witnesses for these corresponding values:

| C header expression | Rust binding expression |
| --- | --- |
| `sizeof(ihk_mc_user_context_t)`, `_Alignof(ihk_mc_user_context_t)` | `size_of::<X86UserContext>()`, `align_of::<X86UserContext>()` |
| `offsetof(ihk_mc_user_context_t, gpr.rdi/rsi/rdx/r10/r8/r9)` | `offset_of!(X86UserContext,gpr) + offset_of!(X86BasicRegs,rdi/rsi/rdx/r10/r8/r9)` |
| `sizeof(struct k_sigaction)`, `_Alignof(struct k_sigaction)` | `size_of::<KSigAction>()`, `align_of::<KSigAction>()` |
| `offsetof(struct k_sigaction,sa.sa_handler)` and `.sa.sa_flags` | `offset_of!(KSigAction,sa) + offset_of!(SigAction,sa_handler/sa_flags)` |
| `__NR_rt_sigaction`, `__NR_rt_sigprocmask` | `13`, `14` |
| `sizeof(unsigned long)`, `sizeof(int)`, `sizeof(long)`, `sizeof(void (*)(int))` | `size_of::<CULong>()`, `size_of::<CInt>()`, `size_of::<CLong>()`, target function-pointer width |

Check `long (*)(unsigned long)` for the mask bridge and
`long (*)(int,const void *)` for the action bridge against the Rust extern C
signatures and final symbol relocations. In addition to width, review function
pointer-to-integer conversion for supported x86 ABI and the exact `SIG_IGN`
representation, callback action/mask field alignment, getter field access,
forwarder target, original callback selection and unchanged debug metadata.
Source-side assertions such as context size224/gpr offset56 and action size32/
flags offset8 are expectations, not a substitute for real-header object proof.
Witness objects, if built, must use separate output paths and be excluded from
all production link inputs. Verify the existing patch's fallback-token and
original metadata claims on the actual composed source and object.

Next executable step after current custody, independent source/operation review
and an explicit resource grant: bind the merged candidate and actual generated
headers, then perform cheap paired ABI/type and symbol/link checks before a
matching current-image functional/native qualification. No current command is
released by this descriptor.
