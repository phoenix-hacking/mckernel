/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../../new-window-source-11/fixture-source/fixture-endpoints.h"
#include "original-lookup.ACTUAL.inc"
struct vm_range *fixture_original_lookup(void *v,unsigned long s,unsigned long e){return arch_process_vm_rw_lookup_range_bridge(v,s,e);}
