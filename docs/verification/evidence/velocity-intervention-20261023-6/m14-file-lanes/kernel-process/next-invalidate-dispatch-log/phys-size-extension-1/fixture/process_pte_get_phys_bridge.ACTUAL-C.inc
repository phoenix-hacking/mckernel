uintptr_t process_pte_get_phys_bridge(void *ptep)
{
	return pte_get_phys((pte_t *)ptep);
}
