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
