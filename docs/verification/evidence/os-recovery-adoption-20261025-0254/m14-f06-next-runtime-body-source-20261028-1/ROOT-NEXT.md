Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private source ready for one actual remaining selected C body:
vdso_get_vdso_info, canonical arch/x86_64/kernel/syscall.c:2965. Read-only nm of
accepted CURRENT115 arch7f53 defines it among18 C functions. calculate_time_from_tsc
is already Rust-selected and its original C excluded; it was not ported again.
The native-specific private Rust vdso initializer is a different protocol route,
not a generic legacy-body successor. It remains byte-unchanged in this proposal.

New f06_vdso_info.rs is a child module of syscall_policy, accessing its actual
ArchVdso definition. It owns the entire original reset/prepare/send/poll/error
flow and exported legacy public symbol. The old C state allocation and reviewed
state-return bridge remain owned where they are. There is no new C body, new
state allocation, Linux bypass, peer protocol change, timeout or guard change.
Only private patches are written; canonical sources are untouched.

The original ABI is LP64: state88/align8; busy signedlong at0, pages signedint
at8, vgtod pointer80. Packet128/align8 with msg8 and traditional arg40. The
existing packet prepare helper writes only msg/arg: stack packet remainder stays
uninitialized as in C; Rust never constructs or reads a whole initialized value.
Flags0 and current CPU channel are passed unchanged. Error signed32 is returned
without transformation, including INT_MIN/MAX. The entire state including
padding is zeroed, then busy1/pages0. Every nonzero error clears only pages;
busy/other peer state is preserved. Busy polling uses read_volatile and the same
pause helper, with no added fences or finite wait replacing the original wait.

Both dynamic debug sites and their strings/function names remain represented
by Rust descriptors; error strings remain unconditional kprintf. Metadata file
and line ownership move to the new Rust module, explicitly requiring the normal
full metadata review. No tracing is disabled or default flags widened. The
original two C descriptors disappear only when the C body selector is enabled.

Three exact future HOST commands are in FUTURE-HOST-COMMANDS.NOT-GRANTED.json.
Root creates its fresh output under the applicable ordinary grant, then compiles
the unchanged extracted C original body with a controlled fake peer, links the
same callbacks to Rust and runs500 deterministic behavior pairs. The oracle
compares return, every state byte, complete debug/error event sequence, pages at
each event, physical/preparation/send counts and completion-pause counts. It
covers prepare and send errors0/-1/-22/INT_MIN/MAX, immediate and1/2/17-pause
completion, and pages0/2/-1/INT_MIN/MAX. The original C body/layout fragments
are extracted verbatim from pinned canonical source. No compiler or fixture was
run in this lane, because the assignment requires an actual ordinary grant.

Concrete Root integration after review: install the module at
kernel/rust/f06_vdso_info.rs and apply syscall-policy-integration.patch,
arch-syscall-selection.patch, and cmake-selection.PROPOSAL.patch to a coherent
current private tree. Generic setup imports the module public entry; native setup
retains its existing private initializer. Build the current production Rust crate
and whole selected arch TU, require one Rust public vdso_get_vdso_info definition,
zero C definition, the original packet/send imports, two correct debug descriptors,
state size/layout and complete metadata. Partial/default linkage and applicable
native proof remain separate gates. Candidate/source readiness closes no file,
changes no accepted image and earns no current default/native/C retirement credit.
