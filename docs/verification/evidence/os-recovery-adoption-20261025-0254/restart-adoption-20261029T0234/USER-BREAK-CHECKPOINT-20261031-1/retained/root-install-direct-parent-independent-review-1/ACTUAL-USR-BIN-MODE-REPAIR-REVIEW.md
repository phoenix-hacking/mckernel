# One-directory functional mode repair review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. This is the independent conditional review consumed by the exact
one-shot release; it is not the actual release and does not assert mutation.

The bound source checks and holds the observed no-follow /usr/bin directory
device 66306/inode 1048578, root:root mode 0777, exact observed ancestry,
mount/namespace and absent access/default ACLs. After durable intent and fresh
revalidation it performs one fchmod to 0755, then fsyncs, checks the named inode
and separately opened readback, and records descriptor close dispositions.
Failure or interrupted mutation remains UNKNOWN; no retry or rollback follows.
No recursive, file, ownership, flag, mount or other directory change is
authorized by this review.

Retained usr-bin-mode-cases-0001 reports seven mock cases PASS, tool exit 0 and
empty owned group. The cases cover metadata/ACL and actual guarded repair
ordering, precheck refusal, single fchmod failure and postmutation output
failure; they perform no real chmod. Root must still obtain the exact separate
fresh one-shot release and independently recheck live controls/usage/caps,
directory device/inode/owner/mode/times/ACLs, mount namespace, current R3
caller/sudo/root identity and child/job count, resource and broker accounting,
and an exclusive capture with positive helper join.

This helper's 64 MiB fits only inside the already reserved current R3 operation
allocation and an actually unused operation role. Preserve original UNKNOWN
four GiB, R3 current four GiB, native12, V2 UNKNOWN two GiB, scratch21 and
mutex27:4. The mode change does not release either reservation or any native,
source-binding or effective-view gate.
