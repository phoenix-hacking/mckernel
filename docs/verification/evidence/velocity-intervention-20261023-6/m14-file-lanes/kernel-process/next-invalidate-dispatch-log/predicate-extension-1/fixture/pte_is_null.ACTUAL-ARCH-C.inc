int pte_is_null(pte_t *ptep)
{
	return (*ptep == PTE_NULL);
}
