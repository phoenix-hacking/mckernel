
static void
arch_process_vm_rw_read_lock_bridge(void *vm)
{
	ihk_rwspinlock_read_lock_noirq(
			&((struct process_vm *)vm)->memory_range_lock);
}

static void
arch_process_vm_rw_read_unlock_bridge(void *vm)
{
	ihk_rwspinlock_read_unlock_noirq(
			&((struct process_vm *)vm)->memory_range_lock);
}

static struct vm_range *
arch_process_vm_rw_lookup_range_bridge(void *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range((struct process_vm *)vm, start, end);
}

static struct process *
arch_process_vm_rw_find_process_bridge(int pid, void *lock_node)
{
	return find_process(pid, (struct mcs_rwlock_node_irqsave *)lock_node);
}

static void
arch_process_vm_rw_process_unlock_bridge(void *proc, void *lock_node)
{
	process_unlock((struct process *)proc,
			(struct mcs_rwlock_node_irqsave *)lock_node);
}

static void
arch_process_vm_rw_update_lock_bridge(void *proc, void *lock_node)
{
	mcs_rwlock_reader_lock_noirq(&((struct process *)proc)->update_lock,
			(struct mcs_rwlock_node *)lock_node);
}

static void
arch_process_vm_rw_update_unlock_bridge(void *proc, void *lock_node)
{
	mcs_rwlock_reader_unlock_noirq(&((struct process *)proc)->update_lock,
			(struct mcs_rwlock_node *)lock_node);
}

static void
arch_process_vm_rw_hold_vm_bridge(void *vm)
{
	hold_process_vm((struct process_vm *)vm);
}

static void
arch_process_vm_rw_release_vm_bridge(void *vm)
{
	release_process_vm((struct process_vm *)vm);
}

static int
arch_process_vm_rw_vtop_bridge(void *page_table, unsigned long virt,
		unsigned long *phys, unsigned long *psize)
{
	return ihk_mc_pt_virt_to_phys_size((struct page_table *)page_table,
			(const void *)virt, phys, psize);
}

static int
arch_process_vm_rw_page_fault_bridge(void *vm, unsigned long addr,
		unsigned long reason)
{
	return page_fault_process_vm((struct process_vm *)vm, (void *)addr,
			reason);
}

static void *
arch_process_vm_rw_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

static void
arch_process_vm_rw_memcpy_bridge(void *dst, const void *src, size_t bytes)
{
	fast_memcpy(dst, src, bytes);
}
