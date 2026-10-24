void original_remote_flush_tlb_array_cpumask(struct process_vm *vm,
		unsigned long *addr,
		int nr_addr,
		int cpu_id)
{
	(void)mem_remote_flush_tlb_array_body_result(vm, addr, nr_addr, cpu_id,
			tlb_flush_vector, IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,
			IHK_TLB_FLUSH_IRQ_VECTOR_START, CPU_SETSIZE,
			mem_tlb_rdtsc_bridge, original_mem_tlb_current_cpu_bridge,
			original_mem_tlb_get_vector_bridge, original_mem_tlb_interrupt_cpu_bridge,
			mem_tlb_noirq_lock_bridge, mem_tlb_noirq_unlock_bridge,
			mem_tlb_atomic_set_bridge, mem_tlb_atomic_inc_bridge,
			mem_tlb_atomic_read_bridge, mem_tlb_flush_single_bridge,
			mem_tlb_flush_all_bridge, mem_tlb_pause_bridge);
}
