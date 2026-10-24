static void dtree(struct rb_node *node, int l) {
	struct vm_range *range;
	if (!node)
		return;

	range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));

	dtree(node->rb_left, l+1);
	kprintf("dtree: %0*d, %p: %lx-%lx\n", l, 0, range, range->start, range->end);
	dtree(node->rb_right, l+1);
}
