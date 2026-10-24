/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY precise reference handback. No allocation/copy/install executes.
 * Future fixture binds original debug selectors and same current Page providers. */
#include <process.h>
#include <rusage_private.h>
#include <memory.h>
#include <ihk/debug.h>
#define __FUNCTION__ "page_fault_process_memory_range"
static void fixture_original_cow_commit(struct vm_range *range,uintptr_t *phys_out,
        size_t pgsize,void *virt,struct page **page_out)
{
    uintptr_t phys=*phys_out;struct page *page=*page_out;
			/* Count COW-source pointed-to by only fileobj
			 *  The steps in test/rusage/005:
			 *  (1) Private-map regular file
			 *  (2) Don't touch the page
			 *  (3) Fork and then the child touches the page
			 *  (4) Page-in the COW-source
			 *  (5) Reach here
			 */
			if (rusage_memory_stat_add(range, phys, pgsize, pgsize)) {
				dkprintf("%lx+,%s: COW-source pointed-to by only fileobj, calling memory_stat_rss_add(),pgsize=%ld\n",
						phys, __FUNCTION__, pgsize);
			}
			if (page) {
				if (page_unmap(page)) {
					dkprintf("%lx-,%s: cow,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", phys, __FUNCTION__, pgsize, pgsize);
					rusage_memory_stat_sub(range->memobj, pgsize, pgsize); 
				}
			}
			phys = virt_to_phys(virt);
			page = phys_to_page(phys);
    *phys_out=phys;*page_out=page;
}
#undef __FUNCTION__
extern void process_page_fault_cow_commit_body_result(struct vm_range *,uintptr_t *,
        size_t,void *,struct page **,struct ddebug *,struct ddebug *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_add),
 int (*)(struct vm_range *,uintptr_t,unsigned long,int)),"actual RSS add types");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),
 void (*)(struct memobj *,unsigned long,int)),"actual RSS sub CULong then CInt");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),
 int (*)(struct page *)),"same old Page consume/unmap provider");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),
 struct page *(*)(uintptr_t)),"remaining actual C lookup provider boundary");
_Static_assert(__builtin_types_compatible_p(__typeof__(&virt_to_phys),
 unsigned long (*)(void *)),"existing actual Rust physical translation export");
_Static_assert(sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,
 "actual supported scalar widths; no new provider signature inference");
