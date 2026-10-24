void process_invalidate_one_page_log_bridge(void *arg0,
		void *page_table, void *ptep, unsigned long pte_value,
		void *pgaddr, int pgshift, int error)
{
	ekprintf("invalidate_one_page(%p,%p,%p %#lx,%p,%d):"
			"invalidate failed. %d\n",
			arg0, page_table, ptep, pte_value, pgaddr, pgshift,
			error);
}
