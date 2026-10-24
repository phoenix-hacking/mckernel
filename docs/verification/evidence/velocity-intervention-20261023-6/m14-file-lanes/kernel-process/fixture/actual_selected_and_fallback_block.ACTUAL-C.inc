#ifdef DEBUG_PRINT_PROCESS
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Existing compile-time dump gate, exposed as readonly ABI data only. */
const int process_dump_tree_enabled = 1;
#else
static void dtree(struct rb_node *node, int l) {
	struct vm_range *range;
	if (!node)
		return;

	range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));

	dtree(node->rb_left, l+1);
	kprintf("dtree: %0*d, %p: %lx-%lx\n", l, 0, range, range->start, range->end);
	dtree(node->rb_right, l+1);
}
static void dump_tree(struct process_vm *vm) {
	kprintf("dump_tree %p\n", vm);
	dtree(vm->vm_range_tree.rb_node, 1);
}
#endif
#else
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
const int process_dump_tree_enabled = 0;
#else
static void dump_tree(struct process_vm *vm) {}
#endif
#endif


