void pte_xchg(pte_t *ptep, pte_t *valp)
{
	*valp = atomic_xchg_ulong(ptep, *valp);
}
