/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Additive source-only actual callback executor; no main/commands/second queue.
 * Provider observation/reset callbacks are test-glue from the existing VM4
 * controller; they do not substitute for the actual old/new init callbacks.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
struct whole_init_capture {unsigned init_calls,prepare_calls,free_calls,phase,error;void *stored;unsigned long start,size,unit;int flag;};
typedef void(*actual_whole_init)(void);
typedef void(*controlled_provider_reset)(void *allocator_return,int prepare_status,void **actual_slot);
typedef void(*controlled_provider_capture)(struct whole_init_capture*);
static int execute_whole_vmap_actual_pair(actual_whole_init original,actual_whole_init replacement,
 void **actual_slot,void *prior,void *allocation_return,int prepare_status,
 controlled_provider_reset reset,controlled_provider_capture capture)
{
 struct whole_init_capture a,b;memset(&a,0,sizeof a);memset(&b,0,sizeof b);
 *actual_slot=prior;reset(allocation_return,prepare_status,actual_slot);original();capture(&a);
 if(*actual_slot!=allocation_return)return 1;
 *actual_slot=prior;reset(allocation_return,prepare_status,actual_slot);replacement();capture(&b);
 return *actual_slot!=allocation_return||a.init_calls!=1||b.init_calls!=1||
 a.prepare_calls!=1||b.prepare_calls!=1||a.free_calls||b.free_calls||
 a.phase!=2||b.phase!=2||a.error||b.error||a.stored!=allocation_return||b.stored!=allocation_return||
 a.start!=b.start||a.size!=b.size||a.unit!=b.unit||a.flag!=b.flag;
}
/* The reset/capture controller MUST record the real slot during prepare before
 * it returns, using the same NULL/live descriptor+negative/zero/positive status
 * cases as the frozen VM4 fixture. Both actual void callbacks above execute;
 * no observer-created store or mapping acknowledgement is permitted. */
