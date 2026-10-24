int process_pte_is_fileoff_bridge(void *ptep, size_t pgsize)
{
	return pte_is_fileoff((pte_t *)ptep, pgsize);
}
