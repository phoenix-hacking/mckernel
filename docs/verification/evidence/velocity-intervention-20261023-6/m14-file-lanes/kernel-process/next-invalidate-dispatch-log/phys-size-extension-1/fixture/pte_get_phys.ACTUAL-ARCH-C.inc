uintptr_t pte_get_phys(pte_t *ptep)
{
	return (*ptep & PT_PHYSMASK);
}
