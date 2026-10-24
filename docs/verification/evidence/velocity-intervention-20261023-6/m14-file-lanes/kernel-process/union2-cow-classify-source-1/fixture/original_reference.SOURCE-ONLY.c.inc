/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY actual original expressions, retaining C short-circuit order. */
#include <process.h>
#include <memobj.h>
int fixture_original_cow_classify(struct vm_range *range,uint64_t reason,struct page *page)
{
    int private_range,patching_to_rdonly;
    int devfile_or_hugetlbfs_or_premap,regfile_or_shm;
	private_range = (range->flag & VR_PRIVATE);
	patching_to_rdonly =
		((reason & PF_PATCH) && !(range->flag & VR_PROT_WRITE));

	/* device file map, hugetlbfs file map, pre-mapped file map */
	devfile_or_hugetlbfs_or_premap =
		(!page &&
		 (range->memobj && !(range->memobj->flags | MF_ZEROOBJ)));

	/* regular file map, Sys V shared memory map */
	regfile_or_shm =
		(page &&
		 (page_is_in_memobj(page) || page_is_multi_mapped(page)));

	if ((private_range || patching_to_rdonly) &&
	    (devfile_or_hugetlbfs_or_premap || regfile_or_shm)) {

        return 1;
    }
    return 0;
}
extern int process_page_fault_cow_classify_body_result(struct vm_range *,uint64_t,struct page *);
_Static_assert(MF_ZEROOBJ==0x20000,"preserved original OR mask");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_is_in_memobj),int (*)(struct page *)),
 "actual borrowed Page predicate signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_is_multi_mapped),int (*)(struct page *)),
 "actual borrowed Page count predicate signature");
_Static_assert(sizeof(uint64_t)==8&&sizeof(unsigned long)==8,"exact supported reason/flag widths");
