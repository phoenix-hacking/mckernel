struct clear_range_args {
	int free_physical;
	struct memobj *memobj;
	struct process_vm *vm;
	unsigned long *addr;
	int nr_addr;
	int max_nr_addr;
};
