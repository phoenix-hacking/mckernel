Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

No app ABI producer defect found. Preserve the app and strict oracle.

The frozen app syscall6 uses rax=number, rdi/rsi/rdx/r10/r8/r9 for the six
arguments, declares rcx/r11 clobbers and does not use nomem. The first getter
is syscall239 with rdi=0 (mode=NULL), rsi=allowed[1..].as_mut_ptr(), rdx=256,
r10=0 (address), r8=4 (MPOL_F_MEMS_ALLOWED), r9=0. The pointer is to the first
of four interior u64 words; the six-word array is inferred as u64 from GUARD.
Its interior occupies offsets8..39 of a48-byte array, bounded by sentinels.

The frozen production source at ../numa-current-image-successor-preparation-
20261021-1/source-materialization-1/materialized-source has the native entry
kernel/rust/syscall_policy.rs:12856 reading rdi/rsi/rdx/r10/r8 in that exact order.
Its validator:8125 treats maxnode as bits: (256+7)&!7=256, clamp to256, then
MEMS_ALLOWED body:8227 copies256>>3=32 bytes. It never touches mode_addr in this
branch, so NULL mode is valid. The process/range policy path is not reached.
MPOL_F_MEMS_ALLOWED is1<<2 at:1652 and kernel/include/process.h:219; syscall_list.h
slot239 selects get_mempolicy. Local installed Linux headers independently match
__NR_get_mempolicy239, __NR_mbind237 and flag4; accepted Linux reference already
ran the exact source with exit37/full116byte expected output/empty stderr.

C/Rust units agree. kernel/rust/abi.rs:5-10 defines CInt=i32, CLong=i64,
CULong=u64, SizeT=usize. Rust get_mempolicy_body_result exposes externC and
passes destination address/source pointer/SizeT bytes to syscall_copy_to_user_bridge.
kernel/syscall.c:298 defines that callback as long(unsigned long,const void*,size_t),
and:19261 forwards bytes unchanged to copy_to_user. The retained C helper at
:12049-12135 has the same bit alignment,256-bit clamp and byte shift; native
production selection uses the Rust entry. This is a focused source ABI join,
not new whole-image or structure-layout acceptance.

Retained native serial ND_PAYLOAD reports normal raw_wait_status256(exit1),
exact stderr FAIL stage=allowed-empty raw=0 unmap_raw=0\n, empty stdout,
both EOFs true and procfs_empty true; it subsequently reports Power down.
The app reaches allowed-empty only after syscall raw0 and sentinel checks.
Therefore, assuming the accepted source/payload binding, its four returned
interior words were zero. That is a source-derived inference: serial contains
no direct syscall239 register/mask dump. It does not show an out-of-range copy
or flags/unit mismatch. munmap returned0; mbind and later interval queries did
not execute. result.json retains FAIL and application_acceptance=false.

No implementation change or patch is justified in this app lane. Native mask
producer/topology/process initialization belongs to the separate assigned lane.
Only read-only source/evidence inspection and these new report files were used;
no replay, compile, test, root, Docker, network or general artifact audit occurred.
