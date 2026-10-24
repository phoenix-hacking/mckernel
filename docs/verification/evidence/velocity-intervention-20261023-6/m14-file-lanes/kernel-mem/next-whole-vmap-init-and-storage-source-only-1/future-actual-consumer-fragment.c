/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only actual whole-wrapper/storage future fixture, no main/driver.
 * Original C bodies are rename-only; Rust bodies use exact C metadata symbols.
 * Reuse real mem_virtual_allocator_init_body_result and the frozen4adapters.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
typedef void *(*allocator_getter)(void);
typedef void(*whole_init)(void);
static int vmap_storage_actual_pair(allocator_getter original,allocator_getter replacement,
 struct ihk_page_allocator_desc **actual_slot,struct ihk_page_allocator_desc *value)
{
 *actual_slot=value;void *a=original();void *b=replacement();
 return a!=(void*)value||a!=b||*actual_slot!=value;
}
struct whole_init_observation {unsigned init_calls,prepare_calls,free_calls,phase,error;void *stored;unsigned long start,size,unit;int flag,status;};
/* Controller recordsactualallocator-init andpublicprepare providerboundaries;
 * inprepare itmustread*actual_slot==exactallocatorreturn, includingNULL. */
static int whole_vmap_init_actual_pair(whole_init original,whole_init replacement,
 struct ihk_page_allocator_desc **actual_slot,struct ihk_page_allocator_desc *prior,
 const struct whole_init_observation *original_trace,const struct whole_init_observation *Rust_trace,
 struct ihk_page_allocator_desc *expected)
{
 /* A future driver runs each callback against freshidenticalproviders/slot and
  * passes the twoobservations here. Callbackexecutioncannotbesimulatedbythese
  * checks; actualold/new functions andactualinitconsumer arelinked. */
 (void)original;(void)replacement;(void)prior;
 return *actual_slot!=expected||original_trace->init_calls!=1||Rust_trace->init_calls!=1||
 original_trace->prepare_calls!=1||Rust_trace->prepare_calls!=1||original_trace->free_calls||Rust_trace->free_calls||
 original_trace->phase!=2||Rust_trace->phase!=2||original_trace->error||Rust_trace->error||
 original_trace->stored!=expected||Rust_trace->stored!=expected||
 original_trace->start!=Rust_trace->start||original_trace->size!=Rust_trace->size||
 original_trace->unit!=Rust_trace->unit||original_trace->flag!=Rust_trace->flag;
}
/* Required: zero/livepointergetter andsuccess/NULLallocatorreturns; prepare
 * statuses -EINVAL/0/1 retainedasprovidertracebutignoredbyBOTHvoidwrappers.
 * Wholewrapperdoesnotfree/retry/skipprepareafterNULL. Metadatawitness checks
 * exactslotaddress&staticvmap_allocator, globalsize/alignment andconfigured
 * MAP_VMAP_START/MAP_VMAP_SIZE/PAGE_SIZE/FIRST_LEVELvalues fromrealheaders.
 * Read/write isplainpointerrepresentation, noexclusiveRustreference orlock.
 * CnonRustfallbackoriginalfunctionbody isretainedbyte-for-byte in#else.
 */
