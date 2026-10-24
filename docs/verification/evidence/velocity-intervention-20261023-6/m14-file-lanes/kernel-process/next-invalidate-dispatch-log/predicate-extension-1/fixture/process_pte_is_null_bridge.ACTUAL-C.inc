int process_pte_is_null_bridge(void *ptep)
{
	return pte_is_null((pte_t *)ptep);
}
