// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Negative compile fixtures, UNRUN. A future harness places each separate
// function in the owner module's PARENT and requires type/privacy diagnostics.
// These are comments so that the production source itself is not changed.
//
// unsafe fn bad_release(lease: perf_group_owner::DescriptorLease) {
//     perf_group_owner::release_pair(lease); // DescriptorLease != BorrowedPair
// }
//
// unsafe fn bad_clone(event: *mut perf_group_owner::EventOwner,
//                     group: *mut perf_group_owner::GroupOwner) {
//     perf_group_owner::duplicate_registered_pair(event, group); // private helper
// }
//
// unsafe fn bad_second_detach(removed: perf_group_owner::RemovedRegistration) {
//     perf_group_owner::abort_unpublished_lease(removed.lease); // field private;
//     // the inner DetachedLease is also not a DescriptorLease
// }
