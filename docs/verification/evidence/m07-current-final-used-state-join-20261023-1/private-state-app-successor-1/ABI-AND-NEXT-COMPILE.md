Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is an implemented private source candidate. No compiler, semantic test,
register instruction, host app, guest, root operation or new acceptance ran.
The old x87/SSE/YMM mask7 evidence remains accepted within its original scope.

The exact retained three-boundary app is C plus `native-vector-enabled-state.S`;
the retained Rust `app1.rs` uses `fp_state.S` for paired yields only. The new Rust
app reuses that Rust app's exact pair-affinity setup and the existing assembly
getpid/FUTEX_WAIT_PRIVATE/FUTEX_WAKE_PRIVATE/self-tgkill sequence. It adds only
component3/4/9 state production and checking; it does not replay mask7.

Eligibility reads CPUID before XGETBV and requires XSAVE+OSXSAVE. MPX additionally
requires CPUID7.MPX, both user-XCR0/D0 component bits, separate nonoverlapping
standard-format 64-byte layouts for3/4, bounded offsets and extent<=4096. PKRU
additionally requires PKU, OSPKE, user-XCR0/D0 bit9 and an8-byte standard layout.
No RDPKRU/WRPKRU is issued, and OSPKE-clear is explicitly NOTEXECUTED9. The
retained0x21f profile therefore cannot earn a PKRU preservation result. Eligibility
is only the prerequisite: immediate real XSAVE readback must also reproduce
noninitial bytes/in-use bits after XRSTOR before any boundary can count.

MPX seed images contain four noninitial lower/encoded-upper pairs and BNDCFGU
with EN=0/BNDPRESERVE=1, zero BNDSTATUS/reserved bytes, distinct canonical unused
directory bases for worker/waker/handler. No bound directory is accessed and no
bounds checking is performed. PKRU changes only key15 bits and preserves original
key0..14 bits captured at the actual assembly entry; worker/waker/handler use
three distinct key15 values. The app allocates no protection keys, assigns no
keyed mappings, and performs no memory-permission checks. Before any future
PKRU runtime, independent execution review must bind this fixed app's ordinary
key0 mapping profile; this source candidate authorizes no execution or inference
from the retained OSPKE-clear exposure.

All area storage uses Rust `repr(C, align(64))`4096-byte boxes. Offsets and sizes
come from CPUID.D and are checked before constructing ranges. Only architecturally
defined component bytes are compared (3:64,4:16,9:4), plus requested XSTATE_BV
bits. XCOMP_BV/reserved seed bytes remain zero. For original initial components,
restoration compares cleared in-use bits without comparing undefined destination
bytes. No general C object layout or kernel ABI is added. Const assertions bind
Context56 bytes, Range24, Report24, Control16 and every assembly-consumed offset.

`component_probe` captures original selected state, patches the PKRU seed from
that snapshot, seeds and reads it back, executes one existing raw boundary,
checks state, then XRSTORs and verifies original selected state before every
controlled Rust ABI return. Distinct waker state is verified on both sides of
raw wake. The bounded waiter is joined before wake errors propagate. The signal
handler uses GPR-only code to seed/read back a third distinct pattern and leaves
it for the existing signal-return mechanism; a delivery+successful-seed marker
is mandatory before interrupted-state comparison. This handler/clobber boundary
is a new candidate requiring independent source/ABI review, not old acceptance.

The normal partial result prints individual successful selected components but
exits77 and reports NOTEXECUTED for every unexecuted component. Exit0 requires all
required0x218 components to pass syscall, blocking futex and signal checks and
all controlled original-state restores. Exit1 means an actual producer/oracle or
boundary failure. External termination or synchronous instruction faults cannot
return through cleanup and are failures, never state-restoration acceptance.

Primary architecture references used for the finite layout/eligibility design:
[Intel instruction extensions reference](https://www.intel.com/content/dam/develop/external/us/en/documents/architecture-instruction-set-extensions-programming-reference-737410.pdf)
and [Intel SDM](https://cdrdv2-public.intel.com/868137/325462-089-sdm-vol-1-2abcd-3abcd-4.pdf).
These support the OS-enabled PKRU and XSAVE-managed MPX distinctions; they are
source design references, not actual machine or preservation observations.

After a separate root grant, the smallest ordinary checks use the retained
Rust1.92 static-app compile argv (`PREDECESSOR-BINDINGS.json`), CPU6 one job,
AS2GiB/CPU60/wall90+6/FSIZE32MiB/NOFILE256/core0/stack2MiB, and owned990807 capture:

1. Compile/run only `eligibility.rs --test`: synthetic retainedOSPKE-clear,
   missing MPX pair/feature, malformed/supervisor/overflow/overlap layouts,
   noninitial distinct seeds, per-component byte corruption and missing in-use
   bits. The semantic-test source invokes no CPUID, XGETBV, XSAVE or XRSTOR;
   no target component state is touched.
2. Compile `app.rs` with exact retained Rust1.92 `-D warnings -C opt-level=1
   -C codegen-units=1 -C target-feature=+crt-static -C relocation-model=static
   -C link-arg=-no-pie -C link-arg=-Wl,-z,noexecstack`. Do not execute it on host.
3. Inspect only component_probe/component_handler ELF/ABI: static/no interpreter,
   non-executable stack, callee-saved GPRs, expected XSAVE/XRSTOR/raw syscall sites,
   no Rust/libc call inside the live interval, and all controlled exits through
   restoration. Source/ABI review and separate guest release remain required.

No profile widening, unsupported-instruction trial, whole-ISA/IFUNC work, new
functional-check ID, changed existing oracle or native/M07 completion is claimed.
