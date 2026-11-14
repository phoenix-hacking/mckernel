# Private settid Rust candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status: prepared source candidate only. No compiler/test/native execution, no lease,
no shared tree integration, no retirement or acceptance claim. Failure family:
settid-port, zero attempted candidates and zero bounded corrections. Stop after
one failed candidate and one bounded correction, then request focused expertise.

## Exact consumer and delta

The sole actual caller in kernel/syscall.c is do_fork at the !newproc->nr_tids
branch inside CLONE_VM, currently line7515. The branch holds threads_lock,
allocates the temporary int[NR_TIDS] and retained mcexec_tid table, calls settid,
handles negative errors before pool adoption, then copies returned TIDs until
zero or NR_TIDS and releases the temporary array. This is the supported existing
shared-VM thread-TID pool path. The helper's thread parameter is unused today;
the candidate preserves that signature and does not dereference it. No caller,
publication, ACK, lock, TID allocation, transport or ownership changes.

Apply ONLY syscall-c.patch and syscall-policy-rs.patch after checking their base
hashes against source-inputs.json (or explicitly rebasing a disjoint change).
The existing MCKERNEL_RUST_SYSCALL_POLICY_HELPERS selection calls the new exported
Rust helper; its old C body remains byte-for-byte in the #else body. Existing
ENABLE_RUST_KERNEL default ON and x86_64 CMake selection already compile
syscall_policy.rs, abi_checks.c and this selection define. No new build toggle,
new module or CMake delta. Rust-off configurations retain the existing C body.

## Exact request/return contract

- C retains exactly `struct syscall_request request IHK_DMA_ALIGN` in the settid
  stack frame. The same address stays live until the synchronous Rust/callback
  chain returns. No Rust replacement allocation, guessed DMA alignment or copy.
- Reuse `crate::abi::SyscallRequest`, not a new representation. Authoritative C:
  kernel/include/syscall.h struct syscall_request. Existing kernel/rust/abi_checks.c
  proves size72, align8, offsets rtid0, ttid4, valid8, number16, args24. Existing
  Rust abi.rs repr(C) and layout assertions prove the same; CInt=i32, CLong=i64,
  CULong=u64 on the selected x86_64 profile. All six args are unsigned long.
- Rust zeros EVERY request byte via write_bytes(size_of::<SyscallRequest>()),
  then writes number from the C-supplied __NR_gettid and args[4] using the signed
  int-to-unsigned-long conversion. rtid/ttid/valid and args0..3 stay zero.
- Rust calls the existing virt_to_phys C bridge on tids exactly once even when
  nr_tids=0 or tids=NULL, then writes args[5], then queries the processor ID,
  then invokes existing do_syscall bridge exactly once with the same request.
  No early validation, null special case, count special case or extra offload.
- Cast the do_syscall C long return to CInt FIRST, then test ret<0, log exactly
  once only if negative, and return the same narrowed int. The minimal C log
  adapter formats the exact original `settid: WARNING: do_syscall returns %d\n`.
  High long bits must never decide whether to log.
- Required direct function pointers and request storage are supplied by the
  sole C adapter; safety preconditions are documented on the unsafe Rust body.
  No extra fallible policy or errno is added.

The private candidate retains existing syscall/cpu.c/process.c correctness and
all compute C fallback behavior. It adds no C compute implementation: only an
extern declaration, existing stack allocation, ABI call and exact log formatter.

## Smallest executable observation proposed

Use the existing reviewed ordinary CPU6/CPU7 unprivileged compile profile and
current pinned nightly-2026-02-18 Rust toolchain; dispatcher owns admission and
execution. There is no requested heavy build, root operation, module or guest.
A standalone focused fixture should extract the COMPLETE original settid body
from base/kernel/syscall.c and the COMPLETE selected C adapter/bridge from the
candidate, compile these in separate translation units with identical callback
stubs, and compare them against the actual new Rust body extracted from
candidate/kernel/rust/syscall_policy.rs. Reuse exact SyscallRequest declaration
and scalar aliases from abi.rs and exact C struct from syscall.h. Do not rewrite
or model either body. Include existing C/Rust layout assertions and use the
reviewed profile's actual IHK_DMA_ALIGN definition when compiling the C units.
The production Rust helper needs only those existing aliases/request type,
size_of, write, addr_of_mut and its existing callback type aliases in this
fixture; no full-kernel unresolved stubs are needed.

Capture all commands/stdout/stderr/status under this directory/check-1, with no
reuse of an existing output. Build the extracted Rust object with the pinned
/nightly/bin/rustc --edition=2021 --crate-type=lib --emit=obj -Cpanic=abort
-Copt-level=2; compile and link the two actual C bodies with the existing C
compiler. Feed identical callbacks and compare BOTH to independent byte/order
assertions. These are 12 bounded cases (CPU alternates0/7):

| nr_tids | tids | long callback return | expected int/log |
|---:|---|---:|---|
|1024|non-null|37|37/none|
|0|NULL|0|0/none|
|-1|non-null|-1|-1/once|
|-2147483648|NULL|-2147483648|-2147483648/once|
|2147483647|non-null|2147483647|2147483647/none|
|1|NULL|4294967295|-1/once|
|0|non-null|4294967296|0/none|
|-1|NULL|4294967333|37/none|
|1|non-null|-4294967296|0/none|
|2|non-null|2147483648|-2147483648/once|
|0|NULL|-2147483649|2147483647/none|
|1024|non-null|-9223372036854775808|0/none|

At do_syscall, independently assert all72 request bytes: zeros except number,
args[4]=(unsigned long)nr_tids and args[5]=the distinctive callback physical
value. Stub virt_to_phys must record its argument even for NULL; CPU query
asserts translation already occurred; do_syscall asserts CPU queried and same
stack request address; log asserts one completed offload and the narrowed int.
Compare exact request bytes, order V/C/D/(L), callback counts, stdout log bytes,
return and untouched tids buffer between C and Rust. The two C translation
units retain function name `settid` so __FUNCTION__ remains authoritative.
Keep the negative/log callback ABI and real C int narrowing intact.

This observation would prove finite actual-body parity only. Subsequent work:
independent ownership/ABI source review, shared source integration, selected
full-crate and actual syscall.c compilation with existing ABI checks, unique
final linked helper definition plus actual settid consumer disassembly, matching
current candidate image, then a fresh supported pthread/TID native observation
with unchanged app oracles. None of these are passed by preparing this candidate
or by passing the standalone fixture. No production C retirement before linked
selected consumer and native proof.

## Frozen executable fixture addendum

The concrete fixture now exists in fixture-1/: original.c and candidate.c retain
the complete actual bodies, actual-helper.rs extracts the actual Rust helper
and existing authoritative ABI declarations, and check.c contains independent
byte/order/return/log oracles for the12cases above. The exact SMP x86_64
memconst.h is copied unchanged; IHK_DMA_ALIGN is empty in this profile. No
fixture alignment value was invented. The linker --wrap adapter records the
C carrier address for that invocation, poisons its72bytes, and forwards the
request/callbacks unchanged to the real Rust helper. do_syscall verifies that
same pointer and independent complete byte contents. It never compares stack
addresses between separate C and Rust invocations.

run_fixture_once.py and FIXTURE-PROPOSAL.json give the exact frozen command
sequence, actual pinned compiler paths, prior ordinary-profile basis and
bounded capture requirements. fixture-inputs.json binds all fixture sources,
runner, compiler/tool binaries and source patches. This is a PROPOSED profile;
root must provide the actual reviewed ordinary grant and outer capture. The
proposal and this document supply no release authority. No compilation, test,
runner import or source integration has been executed.
