unsigned long original_mem_tlb_rdtsc_bridge(void)
{
	return rdtsc();
}

int original_mem_tlb_current_cpu_bridge(void)
{
	return ihk_mc_get_processor_id();
}

int original_mem_tlb_get_vector_bridge(int type)
{
	return ihk_mc_get_vector(type);
}

void original_mem_tlb_interrupt_cpu_bridge(int cpu, int vector)
{
	ihk_mc_interrupt_cpu(cpu, vector);
}

void original_mem_tlb_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

void original_mem_tlb_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

void original_mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value)
{
	ihk_atomic_set((ihk_atomic_t *)atomic_addr, value);
}

void original_mem_tlb_atomic_inc_bridge(unsigned long atomic_addr)
{
	ihk_atomic_inc((ihk_atomic_t *)atomic_addr);
}

void original_mem_tlb_atomic_dec_bridge(unsigned long atomic_addr)
{
	ihk_atomic_dec((ihk_atomic_t *)atomic_addr);
}

int original_mem_tlb_atomic_read_bridge(unsigned long atomic_addr)
{
	return ihk_atomic_read((ihk_atomic_t *)atomic_addr);
}

void original_mem_tlb_flush_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

void original_mem_tlb_flush_all_bridge(void)
{
	flush_tlb();
}

void original_mem_tlb_pause_bridge(void)
{
	cpu_pause();
}

