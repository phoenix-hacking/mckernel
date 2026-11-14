/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future real-TU witness: retain original real kernel include/define options.
 * No compilation, default-consumer or native acceptance is asserted here.
 */
#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#error "selected Rust policy consumer required"
#endif
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-move-pages-log-source-1/candidate/syscall.c"
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8, "x86_64 log widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(&move_pages_log_bridge),
    void (*)(int, unsigned long, int)), "MovePagesLogFn C ABI");
