void process_pte_xchg_bridge(void *ptep, void *valp)
{
	pte_xchg((pte_t *)ptep, (pte_t *)valp);
}
