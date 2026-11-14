/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-destroy-helper-error-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_destroy_helper_failed_panic_bridge),void(*)(void)),"exact helper-failure callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&panic),void(*)(const char*)),"existing Rust panic C declaration");
