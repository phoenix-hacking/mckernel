# Tested matched candidate — 2026-10-19

This local diagnostic candidate boots the fixed FP image with one matching SDK
module set. It is a working baseline for the remaining practical regressions,
not whole-OS completion or a general supported-feature claim.

| Component | Accepted identity |
| --- | --- |
| McKernel image | `1e7a1f689f565e3ba35def32d4f8c9ae729f0e5945c4fbeadee4eb523738a4a2`, 7,933,968 bytes |
| IHK / SMP / mcctrl | Exact complete hashes and original/copy descriptors in the [module manifest](../evidence/current-host-rust-pair-native-20261019-1/MATCHED-MODULE-MANIFEST.json) |
| Host workload | CPUs 2–5, 12 GiB RAM with no additional swap, 512 tasks, no network; one exclusive heavy owner |
| Guest | Four vCPUs, 8,192 MiB, two NUMA nodes; exact boot arguments in the recipe |
| Observed application | One McKernel process, PID255 on CPU0, exit0; exact 380-byte typed AVX output, empty stderr, EOF and empty procfs |
| Diagnostic transfer | McKernel raw ring 49,883 bytes, status219 bytes and control63 bytes; byte-exact decoded transport |

The [recipe](../evidence/current-host-rust-pair-native-20261019-1/SUPPORTED-PROFILE-AND-RECIPE.json)
records the accepted preparation profile, source closure, actual runtime command
mapping and decoder. The [semantic report](../evidence/current-host-rust-pair-native-20261019-1/ACTUAL-MATCHED-THREE-MODULE-TYPED-AVX-AND-RING-TRANSPORT-REVIEW.json)
joins all three real module loads to this image and stage. The separate
[physical report](../evidence/current-host-rust-pair-native-20261019-1/CURRENT-HOST-PAIR-ACTUAL-NATIVE-PHYSICAL-RETIREMENT-REVIEW.json)
accepts process, container and ownership retirement. Closed captures and their
restoration pointers are indexed in the [preservation record](../evidence/current-host-rust-pair-native-20261019-1/preservation-index.json).

For a new invocation, reuse matching retained binaries and archives. Allocate a
fresh short parent, nonce and output paths; validate the complete expanded QEMU
socket paths, current artifact/source descriptors and resource budgets. Prepare
the exact machine request and independent execution decision before the final
live snapshot. The snapshot remains limited to 60 seconds; run the final guard
and owner immediately in the same dispatcher control flow. The consumed example
commands and release are evidence, not commands to replay. Join the owner and
close its streams before the three bounded readers and archive-bound decoder;
a failed owner requires its separately released failure-only readback route.

Remaining claims include native failed-MM-error ownership, complete ring history
and non-null FP allocation/release ownership. Fork/exec/wait remains blocked on
the real provider/revocation/final-ACK path. The practical two-boot, ten-cycle,
100-launch and 60-minute mixed-workload budgets have not been met on this tuple.
No whole ISA, new logical case or additional Rust retirement credit is inferred.
