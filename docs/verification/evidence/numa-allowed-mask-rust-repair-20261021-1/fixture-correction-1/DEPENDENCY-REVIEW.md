Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

ONE bounded correction of fixture-compiler/import-contract after first actual
compile1. Original actual-body-envelope-capture-1/whole.json, source/script/commands,
ABI and baseline.compile.stderr remain unchanged. Kernel candidate da1e612b unchanged.
No second compiler/body execution by this lane; no production/app/module build.

| Complete source dependency | Required binding |
|---|---|
| Actual get_mempolicy_validate | core::ptr::write; EINVAL,EFAULT,MPOL flags,INTERLEAVE,PROCESS_NUMA_MASK_BITS; CULong/CInt. All already present. |
| Actual get_mempolicy_body_result | size_of,write through validator,copy_nonoverlapping; fully-qualified core::ptr::addr_of!/addr_of_mut!,actual ProcessVm/VmRange/VmRangeNumaPolicy and their ABI fields, six callback aliases, all existing constants/log event IDs. All present. |
| Actual policy_mask_zero | core::ptr::write_volatile was missing; now explicitly imported. |
| Actual policy_mask_set | core::ptr::read_volatile and write_volatile were missing; both now explicitly imported. size_of/types/PROCESS_NUMA_MASK_BITS already present. |
| Actual policy_mask_set_all_nodes | Existing zero/set helpers and topology count; no new provider or helper stub. |
| Actual mempolicy_nodemask_bits_is_clamped | CInt/CULong/PROCESS_NUMA_MASK_BITS already present. |
| Whole actual abi.rs and offset assertion | Exact repo ABI copied and existing layout assertions preserved; qualified compiler>=1.92, never old default rustup selection. No assertion removal/feature workaround. |
| Fixture MAIN/callbacks | core::mem::offset_of/zeroed,types/standard macros,copy_nonoverlapping; original complete assertions/cases are BYTE IDENTICAL. No callback/failure/oracle change. |
| Fixture directory | Corrected script lives one child deeper; R points to parent packet for unchanged baseline75b89149/candidateda1e612b. Output root is fresh child directory. |
| Compiler | Root's genuine accepted pinned compiler path/ref required. --rustc remains mandatory, no default selection/fallback/download/retry. Expected1.92+ supports let_else,offset_of,static_mut_refs. Qualification ref/profile binds exact binary/runtime dependencies, not just version string. |

Only corrected script deltas: two volatile imports and script parent-path binding.
All actual body extraction regex, complete six bodies, whole ABI, constants/types,
compile args, stderr retention, baseline bug/candidate expected arrays, original
BIND0x1234/nodes4/max257→baseline0x1234/candidate0xf/clamp256/copy32 assertions,
copyfault/maxnode/guards/VM preservation and ordinary-policy comparisons remain.

Compiler selection is command DATA only, to be root-bound using genuine accepted
app/NUMA compiler evidence. Old /home/holden/.cargo/bin/rustc is forbidden here;
never add feature gates or replace actual ABI to accommodate it. This dependency
review covers every referenced function/type/constant before the single next run.
No huge suite or per-vector review packet. First meaningful next operation is the
same tiny baseline+candidate actual-body check under existing CPU7/1GiB/30CPU/35wall
profile once root binds compiler ref. A second actual family failure stops for
root strategy/expert decision; no further blind bounded corrections.

Root supplied genuine accepted compiler: absolute
/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc
SHA028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1/654904B.
Exact accepted app grant/01-compile command refs are bound in
GENUINE-ACCEPTED-COMPILER-BINDING.json. No compiler executable was reread/probed,
no app rebuilt and no tests executed here. Root chooses this exact command DATA
for the corrected fixture; code deltas remain only volatile imports+parent path.
