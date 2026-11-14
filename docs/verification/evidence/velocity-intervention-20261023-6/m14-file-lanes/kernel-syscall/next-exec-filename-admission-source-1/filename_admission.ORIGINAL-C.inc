	ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm, (unsigned long)filename, 
			(unsigned long)filename+1);

	if (range == NULL || !(range->flag & VR_PROT_READ)) {
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
		kprintf("execve(): ERROR: filename is bad address\n");
		return -EFAULT;
	}
	
	ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
