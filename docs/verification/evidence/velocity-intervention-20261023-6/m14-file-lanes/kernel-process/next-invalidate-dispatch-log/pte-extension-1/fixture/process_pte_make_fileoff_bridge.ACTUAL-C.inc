void process_pte_make_fileoff_bridge(long off, size_t pgsize,
					    void *ptep)
{
	pte_make_fileoff(off, 0, pgsize, (pte_t *)ptep);
}
