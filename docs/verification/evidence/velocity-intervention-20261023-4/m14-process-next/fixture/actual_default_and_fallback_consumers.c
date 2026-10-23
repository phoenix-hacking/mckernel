#include <process.h>
#include <process_helpers.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
int vm_range_insert(struct process_vm *vm, struct vm_range *newrange);
#else
static void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
static void vm_range_insert_dump_bridge(struct process_vm *);
static int vm_range_insert(struct process_vm *vm, struct vm_range *newrange)
{
	return process_vm_range_insert_result(&vm->vm_range_tree, newrange, vm,
			vm_range_insert_log_bridge, vm_range_insert_dump_bridge);
}
#endif

int process_split_range_insert_bridge(struct process_vm *vm,
		struct vm_range *range)
{
	return vm_range_insert(vm, range);
}
int process_add_range_insert_bridge(struct process_vm *vm,
				    struct vm_range *range)
{
	return vm_range_insert(vm, range);
}
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static void vm_range_insert_log_bridge(int e,struct process_vm *v,struct vm_range *n,struct vm_range *r) {(void)e;(void)v;(void)n;(void)r;}
static void vm_range_insert_dump_bridge(struct process_vm *v) {(void)v;}
#endif
