/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY actual C reference fragment. Future host allocator effect provider
 * returns controlled pointers; this does not execute allocator/backend policy. */
#include <process.h>
#include <ihk/debug.h>
const char *const process_page_fault_anon_alloc_file = "held-original-page-fault-process.c";
const int process_page_fault_anon_alloc_line = 2982;
int fixture_original_anon_allocate(struct process_vm *vm, struct vm_range *range,
        uintptr_t fault_addr,uint64_t reason,pte_t **po,void **bo,size_t *so,
        int *ao,void **vo,int *eo)
{
    pte_t *ptep=*po;void *pgaddr=*bo;size_t pgsize=*so;int p2align=*ao;
    void *virt=*vo;int error=*eo;
#line 2977 "held-original-page-fault-process.c"
			size_t npages;

retry:
			npages = pgsize / PAGE_SIZE;
			virt = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT |
					((range->flag & VR_AP_USER) ? IHK_MC_AP_USER : 0), -1, IHK_MC_PG_USER, fault_addr, __FILE__, __LINE__);
			if (!virt && !range->pgshift && (pgsize != PAGE_SIZE)) {
				error = arch_get_smaller_page_size(NULL, pgsize, &pgsize, &p2align);
				if (error) {
					kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(anon) failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
					goto out;
				}
				ptep = NULL;
				pgaddr = (void *)(fault_addr & ~(pgsize - 1));
				goto retry;
			}
			if (!virt) {
				error = -ENOMEM;
				kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate new page. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
				goto out;
			}

#line 1 "anon-allocation-fixture-fragment"
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 0;
out:
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 1;
}
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),
 void *(*)(int,int,unsigned long,int,int,unsigned long,char *,int)),
 "existing actual allocator/tracking ABI, including signed pagecount narrowing");
_Static_assert(IHK_MC_AP_NOWAIT==2&&IHK_MC_AP_USER==0x1000&&IHK_MC_PG_USER==1,
 "same existing allocation flags and user accounting");
_Static_assert(sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(int)==4,
 "actual LP64 retry arithmetic and CInt conversion");
