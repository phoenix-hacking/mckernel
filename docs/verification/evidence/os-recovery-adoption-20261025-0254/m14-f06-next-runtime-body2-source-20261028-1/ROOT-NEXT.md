Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

ONE new private candidate: arch_native_signal_restore_fp_bridge. It is a public
C body in accepted CURRENT115 arch7f53, outside116shmget/117vdso_info. Existing
complete Rust signal dispatch remains separately gated because its recorded
undefined-domain obligations are unresolved. This slice does not touch that
work. No ready Rust public restore_fp successor was found; existing helper
implementations are reused, with no second validator or FP instruction body.

Rust owns the original complete allocation/copy/validation/checked-restore/free
transaction. Public unsigned64/int32 -> signed64 ABI stays exact. It queries
configured xsave size first even when user_address0 selects reset. Existing Rust
buffer_size governs the same -errno and64KiB bound. A nonnegative result requests
bytes+63 using original wrapping size_t bits, then allocator's original int32
narrowing and NOWAIT0x2. Null allocation returns-ENOMEM. Alignment uses original
(pointer+63)&~63 unsigned bits, without creating a reference or changing lifetime.
Every nonzero copy result becomes-EFAULT. Mask and MXCSR are queried only after
successful copy; existing validate receives exact aligned pointer/bytes/config/
mask/MXCSR and checked restore runs only on validate0. Result propagates unchanged.
Every post-allocation path frees the original allocation once; the aligned interior
pointer is never freed. Native hardware/fault-fixup and reset providers are unchanged.

Tracked allocation/free remain actual kmalloc_tracked/kfree_tracked Rust providers.
Their file/line metadata explicitly moves to the new Rust module's actual call
sites. No allocator tracking, error print or cleanup is bypassed. This provenance
change must pass actual production object/line/string/provider checks; it is not
claimed equivalent C-file line ownership. The C fallback source remains intact
when the new paired selector is off. No C implementation is added or expanded.

Three private patches are proposals against actual adopted116 canonical preimages:
arch selection, root Rust module list, and CMake in the same supported profile
branch. Root must merge these disjoint hunks with future117 or whichever current
source it actually adopts. It must rebind genuine origin source/profile bytes
normally; no previous origin receipt or argv hash is silently reused. Native VDSO
initializer, all117 postimages and canonical/shared files remain untouched.

Four prepared HOST commands in FUTURE-HOST-COMMANDS.NOT-GRANTED.json:
first compile a real current kernel-header ABI witness for allocator/free/copy
nominal signatures, LP64/int32, NOWAIT/errno; then compile the verbatim original
C body with mocked effects, compile a Rust test of the exact production core,
and run576 deterministic C/Rust pairs. HOST fixture never invokes hardware,
real usercopy, allocation, module, syscall, IKC, Docker, root or guest effects.
It compares return, every event argument/order and full65536+128B buffer/canary
state. It varies null/non-null user, negative/512/576/65536 sized result,
allocator failure, copy0/+1/-1, validator0/-22, restore0/-14 and allocation
alignment0/1/63. Independent assertions require configured-first, reset-only,
and exactly one original-pointer free only after successful allocation.

The fixture mocks callbacks, including an arbitrary positive size result with a
fixed configured size, to test caller preservation. It does not claim the real
validator accepts those combinations. Real existing buffer-size/format behavior
is reused unchanged; production and matching native signal-return qualification
remain separate. No compile or fixture has run in this lane: a fresh actual
ordinary grant is required. The first genuine-header ABI compile is the next
executable check. Full production wrappers are excluded by cfg(test) in the
fixture; later fullcrate/selectedTU/defaultlink checks must compile them.

Removal condition: actual selected arch C TU defines no
arch_native_signal_restore_fp_bridge; exactly one new Rust public provider
resolves native sys_rt_sigreturn, with original size/validator/copy/checked-XRSTOR/
reset/MXCSR/tracked-allocator imports and call ordering verified. Keep existing
C fallback for other profiles. Observe matched signal-return and ownership
lifecycle on the current candidate before declaring runtime retirement. This
source predicts one C-function removal only; actual C/default/native/file deltas
are0 and no whole-file or percentage claim follows. Preserve all original
failures/evidence, dirtytree, scratch21 and permanent27:4; Root owns actual
integration, grants, resources, Git, release and current clocks.
