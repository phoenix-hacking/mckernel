Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

BODY11 moves BODY10's remaining32-byte arch_prctl diagnostic descriptor into one
Rust `Ddebug` static in `__verbose`. `f06_prctl_log.rs` is byte-identical to
BODY10, as is the original C function oracle. The existing origin producer supplies
MCKERNEL_F06_RT_SIGRETURN_ORIGIN; line669/flags0/nullfmt/file/function and zero
padding must match the accepted CURRENT116 record. This reuses actual Ddebug and
kprintf providers. C bitfield consumers keep the same address/representation and
original update/exclusion rules; no lock or atomicity promise is added.

This private packet contains canonical118+BODY10+BODY11 full selection patches,
AND BODY11-DELTA-ON-BODY10 patches. Apply ONE path. Preserve frozen cumulative
BODY3-9 and its rebase118 BODY4; Root composes those disjoint additions with this
packet, retaining one storage owner per target and all numeric line restores.
No shared/canonical source was written. All nine canonical118 postimages remain
pinned. BODY10 comments mention the qualified C descriptor ABI; the immutable
callback now imports the identical Rust-owned representation when BODY11 is selected.

Selections: MCKERNEL_RUST_F06_PRCTL_LOG still selects the existing logger;
MCKERNEL_RUST_F06_PRCTL_LOG_STORAGE selects its Rust storage and extern-only C
consumer declaration. With storage disabled, the exact BODY10 C record remains.
With logger disabled, the original C function+macro/local record remains. The
CMake proposal enables the pair together, with cfg f06_prctl_log_storage_candidate,
module and source dependency. Static initialization has no constructor or teardown.
Original descriptor is image-lifetime; C consumers and Rust logger keep raw accesses.

Nearest actual check is the four exact ordinary HOST commands in
FUTURE-HOST-COMMANDS.json: real Rust object, genuine-header C oracle/consumer
partial link using -save-temps, Rust fixture compile, one fixture run. The oracle
retains its own original LOCAL C descriptor; the selected record must have exactly
one GLOBAL Rust definition. Two HOST records are intentional and do not imply two
selected production records. All output and descriptor mutations are mock HOST
storage. This packet never accesses actual kernel flags, hardware or providers.

After HOST qualification, Root's next source step is compose BODY11 delta with
BODY10 and frozen cumulative packet; update exact F06 origin source/profile/argv
bindings using the existing producer/encoder. Next artifact check is the genuine
selected/fallback C TU, full Rust crate and default partial/final image link with
all existing registry assertions. Require exactly389record multiset, one GLOBAL
32B/align8 Rust __verbose target and no selected C definition/constructor, then
matching-current native functional diagnostics and configuration proof. Source and
HOST checks never close default/native/data/file retirement. Actual accepted
CURRENT116 remains C71/Rust68, arch selected C17 and M14files4/6; the descriptor
remains accepted Cdata until a qualifying default artifact/native result.

Remaining independent body debt after queued BODY3-10 remains arch_ptrace_regset_log_bridge
(original %x/long defined-domain contract missing), arch_vdso_map_log_bridge
(dynamic descriptor/offset/pid contract), and held arch_rt_sigreturn_xrstor_bridge,
arch_native_signal_bad_frame_bridge, arch_rt_sigreturn_context_bridge and do_signal.
BODY11 adds storage ownership, not a new function-retirement count. Held domains,
original failures, scratch21/permanent27:4 and retained BFD physical pending remain.
