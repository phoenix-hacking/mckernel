#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Keep the displaced dynamic-debug selector as declarative C ABI data.
 * Rust owns both event branches, field reads and the existing variadic logger.
 * The source-bound original success callsite remains selectable at line 2086.
 */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_vm_range_insert_debug = {
    .file = __FILE__,
    .func = "vm_range_insert_log_bridge",
    .line = 2086,
    .flags = DDEBUG_DEFAULT,
};
extern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_log_bridge(int event, struct process_vm *vm,
				       struct vm_range *newrange,
				       struct vm_range *range)
{
	if (event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP) {
		ekprintf("vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n",
				vm, newrange->start, newrange->end, newrange->flag,
				range->start, range->end, range->flag);
	}
	else if (event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS) {
		dkprintf("vm_range_insert: %p,%p: %lx-%lx %x\n", vm,
				newrange, newrange->start, newrange->end,
				newrange->flag);
	}
}
#endif
void (*const actual_log_consumer)(int,struct process_vm *,struct vm_range *,struct vm_range *)=vm_range_insert_log_bridge;
