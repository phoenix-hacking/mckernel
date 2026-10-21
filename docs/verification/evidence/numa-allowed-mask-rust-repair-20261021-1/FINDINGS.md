Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Cause-supported minimal Rust proposal only; no integration, compile, app, guest,
root, cleanup or source-body comparison executed by this lane. Root owns those.

Concrete defect: get_mempolicy_body_result flags==MPOL_F_MEMS_ALLOWED returns the
allocation-policy vm.numa_mask. That object is not an allowed-node set. A policy
nodemask may be empty for DEFAULT or restricted for BIND/PREFERRED/INTERLEAVE while
the allowed topology remains unchanged. Current actual McKernel topology has1
assigned dense local node; allowed mask must therefore contain that node even if
the process policy mask is empty. Keep the strict existing nonempty app oracle.

Actual capture only proves flags4 query raw0 copied all-zero4words with guards
intact; baseline/mbind never ran. It does not reveal the last policy-mask writer.
The source contract defect is independently sufficient; do not claim initial VM
memory is uninitialized or a particular host policy branch executed in this guest.

| Source path | Production causal trace |
|---|---|
| arch/x86_64/kernel/include/syscall_list.h:135 | Slot239 SYSCALL_HANDLED get_mempolicy. |
| kernel/rust/syscall_policy.rs:12856 | Current syscall wrapper reads rdi/rsi/rdx/r10/r8 and passes thread.vm plus ihk_mc_get_nr_numa_nodes. Independent app-ABI lane found no call defect. |
| ihk/linux/driver/smp/smp-driver.c:1858,2626,540,610 | Assigned CPU/memory physical nodes enter os.numa_mask; boot nr_numa_nodes=hweight64; published dense McKernel node descriptors. No host-node-number assumption. |
| ihk/cokernel/smp/x86_64/setup.c:326 | Topology getter reads actual boot_param.nr_numa_nodes. Actual serial line870 has cpus1/numa1/chunks2. |
| kernel/rust/process_helpers.rs:6354,6386,6440 | VM initialization zeros then sets all configured local node bits; DEFAULT mode. Initializer itself does NOT intentionally leave a positive topology empty. C process wrapper passes topology; Rust production export passes same. |
| kernel/rust/host_helpers.rs:1805,1806,1900 | Explicit process-policy publication writes supplied mode then clears/copies supplied nodemask, so legal DEFAULT empty descriptor can replace initialization. Bind publication separately copies bind mask. Unspecified loader mode PLD_MPOL_MAX skips overwrite. Actual last writer remains unproven. |
| executer/user/mcexec.c:2301,2330,5494,5518 | Unspecified mode sentinel5; explicit localalloc uses DEFAULT0 with empty nodemask. Sentinel agrees with kernel MPOL_MAX5; no sentinel ABI discrepancy found. |
| kernel/rust/syscall_policy.rs:7745,7783,7807 | set_mempolicy modifies process allocation policy mask; it cannot define independent allowed nodes. |
| kernel/rust/process_helpers.rs:7348 / kernel/process.c:1077 | Fork copies parent's policy mode+mask; sharing/inheritance preserves process policy semantics. |
| kernel/rust/syscall_policy.rs:8227 | Defective allowed-query branch directly copies vm.numa_mask; modeNULL accepted/copy32 correct. |

Minimal patch in allowed-mask-policy-separation.patch changes only that branch:
create local4word mask and use EXISTING policy_mask_set_all_nodes(mask,nr_numa_nodes)
then copy that mask. Uses configured dense OS topology, no hardcoded node, no
fallback, no VM mutation, no extra field/ABI/export/C implementation. Validations,
maxnode/clamp/copyfault/length/guards/normal and address-policy paths unchanged.
Zero topology stays zero; no invented node masks a future topology defect. This
supported profile has no separate per-task cpuset allowed mask; future independent
cpuset restrictions require their own source of truth, not process mempolicy bits.

Baseline syscall_policy75b89149 matches actual current source; proposed private
fullfileda1e612b is not live integration. Process/host producers remain unchanged.
Accepted cpu.c/process.c fixes and all failed inputs/oracles remain preserved.

CHEAPEST NEXT MEANINGFUL BODY OBSERVATION (not run here): root reviews this patch,
then run propose_actual_body_comparison.py under the existing ordinary CPU7/onejob/
1GiB/30CPU/35wall envelope in CHECK-PROPOSAL.json. It follows existing source-bound
actual-function pattern in kernel/rust/tests/do_munmap_host_clear_actual_harness.py,
uses complete actual get_mempolicy body+validate+mask dependencies and actual abi.rs,
and compiles two tiny ordinary test binaries. Baseline must reproduce policy-dependent
empty-mask bug; candidate must match independent explicit topology arrays for all
four policies, preserve VM mode/mask and guards, copy32, copyfault/maxnode behavior.
The EXACT original equivalence vector BIND0x1234/nodes4/maxnode257 is retained:
baseline0x1234, candidate0xf, both clamp-log256/copy32. No kernel/module/app build.

C REFERENCE BOUNDARY: kernel/syscall.c:12129 has the SAME legacy policy-mask bug.
run_equivalence.sh:31380 records this exact old behavior in common digest; candidate
must intentionally diverge on that vector. Do not run huge unchanged suite just to
rediscover this deterministic semantic delta. Do not change/sort/mask outputs or
silently edit C reference. After focused positive and peer decision, the existing
fixture should explicitly assert original C behavior0x1234 and independently assert
corrected Rust topology0xf for that specific semantic case, preserving original
vector/failure evidence; all unchanged ordinary policy cases retain C parity. It
must not remove the vector or weaken either assertion. Root owns that integration.

Actual body compile/results, whole-crate/current-image link and unchanged native
application remain pending. Existing launcher689dcad2/toolchain can be reused; only
matching kernel Rust/link inputs require change. No native/application/Rust path
retirement acceptance from source proposal or test plan. Keep oneheavy reviewed
4CPU/12GiB/noSwap/512tasks, CPU7 ordinary, floors+growth, scratchUUID110GiB/noresize,
scratch21/exclusions, permanent mutex27:4 and all original failures. One failed
native candidate is preserved; no unchanged native replay; any next family
failure needs convergence accounting before more attempts.
