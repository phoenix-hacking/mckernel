/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY reference fragment. Actual original pre-error statements extracted
 * verbatim; wrapper exposes the exact new handback, not a zeroobj model. */
#include <process.h>
#include <memobj.h>
int fixture_original_memobj_get(struct vm_range *range,void *pgaddr,uintptr_t fault_addr,
        pte_t *ptep,size_t pgsize,int p2align,uintptr_t *po,unsigned long *fo,int *eo)
{
    uintptr_t phys=*po;unsigned long memobj_flag=*fo;int error=*eo;
		phys = NOPHYS;
		if (range->memobj) {
			off_t off;

			if (!ptep || !pte_is_fileoff(ptep, pgsize)) {
				off = range->objoff + ((uintptr_t)pgaddr - range->start);
			}
			else {
				off = pte_get_off(ptep, pgsize);
			}
			error = memobj_get_page(range->memobj, off, p2align,
                                       &phys, &memobj_flag, fault_addr);

            *po=phys;*fo=memobj_flag;*eo=error;return error!=0;
        }
    *po=phys;*fo=memobj_flag;return 0;
}
extern int process_page_fault_memobj_get_body_result(struct vm_range *,void *,uintptr_t,pte_t *,size_t,int,uintptr_t *,unsigned long *,int *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&memobj_get_page),
 int (*)(struct memobj *,off_t,int,uintptr_t *,unsigned long *,uintptr_t)),
 "exact actual memobj provider output/offset signature");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(off_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,
 "actual supported wrapped-offset/output ABI");
_Static_assert(NOPHYS==(uintptr_t)-1,"same actual no-physical sentinel");
