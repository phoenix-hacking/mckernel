/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-set-page-log-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_set_page_log_bridge),x86_pt_set_page_log_fn_t),"actual typed EBUSY callback ABI");
_Static_assert(sizeof(unsigned long)==8 && sizeof(int)==4,"existing log vararg widths");
