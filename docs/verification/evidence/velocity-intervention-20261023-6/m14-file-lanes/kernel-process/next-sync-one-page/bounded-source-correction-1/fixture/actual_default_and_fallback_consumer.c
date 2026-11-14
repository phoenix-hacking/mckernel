/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
struct sync_args {
	struct memobj *memobj;
};

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Displaced sync callback dynamic-debug selectors: declarative data only. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_entry_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = 2546, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_exit_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = 2574, .flags = DDEBUG_DEFAULT,
};
#else
int sync_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		  void *pgaddr, int pgshift)
{
	struct sync_args *args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	uintptr_t phys;

	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	if (pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)
			|| !pte_is_dirty(ptep, pgsize)) {
		error = 0;
		goto out;
	}

	pte_clear_dirty(ptep, pgsize);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	phys = pte_get_phys(ptep);
	if (args->memobj->flags & MF_ZEROFILL) {
		error = 0;
		goto out;
	}

	error = memobj_flush_page(args->memobj, phys, pgsize);
	if (error) {
		ekprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):"
				"flush failed. %d\n",
				arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
		pte_set_dirty(ptep, pgsize);
		goto out;
	}

	error = 0;
out:
	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}
#endif
