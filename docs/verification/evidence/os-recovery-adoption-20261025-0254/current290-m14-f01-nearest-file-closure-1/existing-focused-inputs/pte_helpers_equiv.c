#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))
#define PTL4_SHIFT 39
#define PTL3_SHIFT 30
#define PTL2_SHIFT 21
#define PTL1_SHIFT 12
#define PTL4_SIZE (1UL << PTL4_SHIFT)
#define PTL3_SIZE (1UL << PTL3_SHIFT)
#define PTL2_SIZE (1UL << PTL2_SHIFT)
#define PTL1_SIZE (1UL << PTL1_SHIFT)
#define PT_PHYSMASK (((1UL << 52) - 1) & PAGE_MASK)
#define PTE_NULL 0UL
#define PM_STATUS_OFFSET 61
#define PM_STATUS_MASK 0xe000000000000000UL
#define PM_PSHIFT_OFFSET 55
#define PM_PSHIFT_MASK 0x1f80000000000000UL
#define PM_PFRAME_MASK 0x007fffffffffffffUL
#define PF_PRESENT 0x01UL
#define PF_WRITABLE 0x02UL
#define PFLX_PWT 0x08UL
#define PFLX_PCD 0x10UL
#define PFL1_PWT PFLX_PWT
#define PFL1_PCD PFLX_PCD
#define PFL1_DIRTY 0x40UL
#define PFL1_FILEOFF (1UL << 11)
#define PFL2_DIRTY 0x40UL
#define PFL2_SIZE_FLAG 0x80UL
#define PFL2_FILEOFF (1UL << 11)
#define PFL3_DIRTY 0x40UL
#define PFL3_SIZE_FLAG 0x80UL
#define PFL3_FILEOFF (1UL << 11)
#define PTATTR_ACTIVE 0x01UL
#define PTATTR_WRITABLE 0x02UL
#define PTATTR_USER 0x04UL
#define PTATTR_DIRTY 0x40UL
#define PTATTR_LARGEPAGE 0x80UL
#define PTATTR_FILEOFF PFL2_FILEOFF
#define PTATTR_NO_EXECUTE 0x8000000000000000UL
#define PTATTR_UNCACHABLE 0x10000UL
#define PTATTR_WRITE_COMBINED 0x40000UL
#define EINVAL 22

unsigned long attr_mask = PTATTR_ACTIVE | PTATTR_WRITABLE | PTATTR_USER |
	PTATTR_DIRTY | PTATTR_FILEOFF | PTATTR_NO_EXECUTE;

struct vm_regions {
	unsigned long vm_start, vm_end;
	unsigned long text_start, text_end;
	unsigned long data_start, data_end;
	unsigned long brk_start, brk_end, brk_end_allocated;
	unsigned long map_start, map_end;
	unsigned long stack_start, stack_end;
	unsigned long user_start, user_end;
};

extern unsigned long STACK_TOP(const struct vm_regions *);
extern unsigned long PM_STATUS(unsigned long);
extern unsigned long PM_PSHIFT(unsigned long);
extern unsigned long PM_PFRAME(unsigned long);
extern unsigned long ALIGN_DOWN(unsigned long, unsigned long);
extern unsigned long ALIGN_UP(unsigned long, unsigned long);
extern int pfn_is_write_combined(uintptr_t pfn);
extern int pte_is_null(unsigned long *ptep);
extern int pte_is_present(unsigned long *ptep);
extern int pte_is_writable(unsigned long *ptep);
extern int pte_is_dirty(unsigned long *ptep, size_t pgsize);
extern int pte_is_fileoff(unsigned long *ptep, size_t pgsize);
extern void pte_update_phys(unsigned long *ptep, unsigned long phys);
extern uintptr_t pte_get_phys(unsigned long *ptep);
extern long pte_get_off(unsigned long *ptep, size_t pgsize);
extern unsigned long pte_get_attr(unsigned long *ptep, size_t pgsize);
extern void pte_make_null(unsigned long *ptep, size_t pgsize);
extern void pte_make_fileoff(long off, unsigned long ptattr, size_t pgsize,
			     unsigned long *ptep);
extern void pte_xchg(unsigned long *ptep, unsigned long *valp);
extern void pte_clear_dirty(unsigned long *ptep, size_t pgsize);
extern void pte_set_dirty(unsigned long *ptep, size_t pgsize);
extern int pte_is_contiguous(unsigned long *ptep);
extern int pgsize_is_contiguous(size_t pgsize);
extern int pgsize_to_tbllv(size_t pgsize);
extern int pgsize_to_pgshift(size_t pgsize);
extern size_t tbllv_to_pgsize(int level);
extern size_t tbllv_to_contpgsize(int level);
extern int tbllv_to_contpgshift(int level);
extern unsigned long *get_contiguous_head(unsigned long *ptep, size_t pgsize);
extern unsigned long *get_contiguous_tail(unsigned long *ptep, size_t pgsize);
extern int page_is_contiguous_head(unsigned long *ptep, size_t pgsize);
extern int page_is_contiguous_tail(unsigned long *ptep, size_t pgsize);
extern void arch_adjust_allocate_page_size(void *pt, uintptr_t fault_addr,
					   unsigned long *ptep, void **pgaddrp,
					   size_t *pgsizep);

#ifdef USE_C_PTE_MODEL
unsigned long STACK_TOP(const struct vm_regions *region)
{
	return region->user_end;
}
unsigned long PM_STATUS(unsigned long nr)
{
	return (nr << PM_STATUS_OFFSET) & PM_STATUS_MASK;
}
unsigned long PM_PSHIFT(unsigned long x)
{
	return (x << PM_PSHIFT_OFFSET) & PM_PSHIFT_MASK;
}
unsigned long PM_PFRAME(unsigned long x)
{
	return x & PM_PFRAME_MASK;
}
unsigned long ALIGN_DOWN(unsigned long x, unsigned long align)
{
	return x & ~(align - 1);
}
unsigned long ALIGN_UP(unsigned long x, unsigned long align)
{
	return ALIGN_DOWN(x + align - 1, align);
}
int pfn_is_write_combined(uintptr_t pfn)
{
	return (pfn & PFL1_PWT) && !(pfn & PFL1_PCD);
}
int pte_is_null(unsigned long *ptep) { return *ptep == PTE_NULL; }
int pte_is_present(unsigned long *ptep) { return !!(*ptep & PF_PRESENT); }
int pte_is_writable(unsigned long *ptep) { return !!(*ptep & PF_WRITABLE); }
int pte_is_dirty(unsigned long *ptep, size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE: return !!(*ptep & PFL1_DIRTY);
	case PTL2_SIZE: return !!(*ptep & PFL2_DIRTY);
	case PTL3_SIZE: return !!(*ptep & PFL3_DIRTY);
	default: return !!(*ptep & PTATTR_DIRTY);
	}
}
int pte_is_fileoff(unsigned long *ptep, size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE: return !!(*ptep & PFL1_FILEOFF);
	case PTL2_SIZE: return !!(*ptep & PFL2_FILEOFF);
	case PTL3_SIZE: return !!(*ptep & PFL3_FILEOFF);
	default: return !!(*ptep & PTATTR_FILEOFF);
	}
}
void pte_update_phys(unsigned long *ptep, unsigned long phys)
{
	*ptep = (*ptep & ~PT_PHYSMASK) | (phys & PT_PHYSMASK);
}
uintptr_t pte_get_phys(unsigned long *ptep) { return *ptep & PT_PHYSMASK; }
long pte_get_off(unsigned long *ptep, size_t pgsize)
{
	(void)pgsize;
	return (long)(*ptep & PAGE_MASK);
}
unsigned long pte_get_attr(unsigned long *ptep, size_t pgsize)
{
	unsigned long attr = *ptep & attr_mask;
	if (*ptep & PFLX_PWT) {
		if (*ptep & PFLX_PCD)
			attr |= PTATTR_UNCACHABLE;
		else
			attr |= PTATTR_WRITE_COMBINED;
	}
	if (((pgsize == PTL2_SIZE) && (*ptep & PFL2_SIZE_FLAG)) ||
	    ((pgsize == PTL3_SIZE) && (*ptep & PFL3_SIZE_FLAG)))
		attr |= PTATTR_LARGEPAGE;
	return attr;
}
void pte_make_null(unsigned long *ptep, size_t pgsize)
{
	(void)pgsize;
	*ptep = PTE_NULL;
}
void pte_make_fileoff(long off, unsigned long ptattr, size_t pgsize,
		      unsigned long *ptep)
{
	unsigned long attr = ptattr & ~PAGE_MASK;
	switch (pgsize) {
	case PTL1_SIZE: attr |= PFL1_FILEOFF; break;
	case PTL2_SIZE: attr |= PFL2_FILEOFF | PFL2_SIZE_FLAG; break;
	case PTL3_SIZE: attr |= PFL3_FILEOFF | PFL3_SIZE_FLAG; break;
	default: attr |= PTATTR_FILEOFF; break;
	}
	*ptep = ((unsigned long)off & PAGE_MASK) | attr;
}
void pte_xchg(unsigned long *ptep, unsigned long *valp)
{
	unsigned long old = *ptep;
	*ptep = *valp;
	*valp = old;
}
void pte_clear_dirty(unsigned long *ptep, size_t pgsize)
{
	unsigned long mask;
	switch (pgsize) {
	default:
	case PTL1_SIZE: mask = ~PFL1_DIRTY; break;
	case PTL2_SIZE: mask = ~PFL2_DIRTY; break;
	case PTL3_SIZE: mask = ~PFL3_DIRTY; break;
	}
	__sync_fetch_and_and(ptep, mask);
}
void pte_set_dirty(unsigned long *ptep, size_t pgsize)
{
	unsigned long mask;
	switch (pgsize) {
	default:
	case PTL1_SIZE: mask = PFL1_DIRTY; break;
	case PTL2_SIZE: mask = PFL2_DIRTY; break;
	case PTL3_SIZE: mask = PFL3_DIRTY; break;
	}
	__sync_fetch_and_or(ptep, mask);
}
int pte_is_contiguous(unsigned long *ptep) { (void)ptep; return 0; }
int pgsize_is_contiguous(size_t pgsize) { (void)pgsize; return 0; }
int pgsize_to_tbllv(size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE: return 1;
	case PTL2_SIZE: return 2;
	case PTL3_SIZE: return 3;
	case PTL4_SIZE: return 4;
	default: return 0;
	}
}
int pgsize_to_pgshift(size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE: return PTL1_SHIFT;
	case PTL2_SIZE: return PTL2_SHIFT;
	case PTL3_SIZE: return PTL3_SHIFT;
	case PTL4_SIZE: return PTL4_SHIFT;
	default: return -EINVAL;
	}
}
size_t tbllv_to_pgsize(int level)
{
	switch (level) {
	case 1: return PTL1_SIZE;
	case 2: return PTL2_SIZE;
	case 3: return PTL3_SIZE;
	case 4: return PTL4_SIZE;
	default: return 0;
	}
}
size_t tbllv_to_contpgsize(int level) { (void)level; return 0; }
int tbllv_to_contpgshift(int level) { (void)level; return 0; }
unsigned long *get_contiguous_head(unsigned long *ptep, size_t pgsize)
{
	(void)pgsize;
	return ptep;
}
unsigned long *get_contiguous_tail(unsigned long *ptep, size_t pgsize)
{
	(void)pgsize;
	return ptep;
}
int page_is_contiguous_head(unsigned long *ptep, size_t pgsize)
{
	(void)ptep;
	(void)pgsize;
	return 0;
}
int page_is_contiguous_tail(unsigned long *ptep, size_t pgsize)
{
	(void)ptep;
	(void)pgsize;
	return 0;
}
void arch_adjust_allocate_page_size(void *pt, uintptr_t fault_addr,
				    unsigned long *ptep, void **pgaddrp,
				    size_t *pgsizep)
{
	(void)pt;
	(void)fault_addr;
	(void)ptep;
	(void)pgaddrp;
	(void)pgsizep;
}
#endif

static void require(int cond)
{
	if (!cond)
		exit(2);
}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

int main(void)
{
	struct vm_regions region = { .user_end = 0x7fff0000UL };
	unsigned long pte = 0;
	unsigned long new_pte;
	unsigned long digest = 0x70746568656c70UL;
	void *pgaddr = (void *)0x1234UL;
	size_t pgsize = PTL2_SIZE;

	require(STACK_TOP(&region) == region.user_end);
	require(PM_STATUS(4) == 0x8000000000000000UL);
	require(PM_STATUS(2) == 0x4000000000000000UL);
	require(PM_PSHIFT(PAGE_SHIFT) == 0x0600000000000000UL);
	require(PM_PFRAME(0x8123456789abcdefUL) == 0x0023456789abcdefUL);
	require(ALIGN_DOWN(0x12345UL, 0x1000UL) == 0x12000UL);
	require(ALIGN_UP(0x12345UL, 0x1000UL) == 0x13000UL);
	mix(&digest, STACK_TOP(&region));
	mix(&digest, PM_STATUS(4));
	mix(&digest, PM_PSHIFT(PAGE_SHIFT));
	mix(&digest, PM_PFRAME(0x8123456789abcdefUL));
	mix(&digest, ALIGN_DOWN(0x12345UL, 0x1000UL));
	mix(&digest, ALIGN_UP(0x12345UL, 0x1000UL));

	require(pte_is_null(&pte));
	require(pfn_is_write_combined(PFL1_PWT));
	require(!pfn_is_write_combined(PFL1_PWT | PFL1_PCD));

	pte = 0x12345000UL | PF_PRESENT | PF_WRITABLE | PFLX_PWT;
	require(pte_is_present(&pte));
	require(pte_is_writable(&pte));
	require(pte_get_phys(&pte) == 0x12345000UL);
	pte_update_phys(&pte, 0xabcdef000UL);
	require(pte_get_phys(&pte) == 0xabcdef000UL);
	mix(&digest, pte_get_attr(&pte, PTL1_SIZE));

	pte_set_dirty(&pte, PTL2_SIZE);
	require(pte_is_dirty(&pte, PTL2_SIZE));
	pte_clear_dirty(&pte, PTL2_SIZE);
	require(!pte_is_dirty(&pte, PTL2_SIZE));

	pte = 0x4000UL | PF_PRESENT | PF_WRITABLE | PFLX_PWT | PFLX_PCD |
		PFL2_SIZE_FLAG;
	require((pte_get_attr(&pte, PTL2_SIZE) & PTATTR_UNCACHABLE) != 0);
	require((pte_get_attr(&pte, PTL2_SIZE) & PTATTR_LARGEPAGE) != 0);
	mix(&digest, pte_get_attr(&pte, PTL2_SIZE));

	pte_make_fileoff(0x1234567L, PTATTR_USER | PTATTR_NO_EXECUTE,
			 PTL2_SIZE, &pte);
	require(pte_is_fileoff(&pte, PTL2_SIZE));
	require(pte_get_off(&pte, PTL2_SIZE) == 0x1234000L);
	require((pte & PFL2_SIZE_FLAG) != 0);
	mix(&digest, pte);

	new_pte = 0xcafe000UL | PF_PRESENT;
	pte_xchg(&pte, &new_pte);
	require(pte == (0xcafe000UL | PF_PRESENT));
	require(new_pte == ((0x1234567UL & PAGE_MASK) | PTATTR_USER |
			PFL2_FILEOFF | PFL2_SIZE_FLAG));
	mix(&digest, pte);
	mix(&digest, new_pte);

	require(pgsize_to_tbllv(PTL1_SIZE) == 1);
	require(pgsize_to_tbllv(PTL4_SIZE) == 4);
	require(pgsize_to_tbllv(123) == 0);
	require(pgsize_to_pgshift(PTL3_SIZE) == PTL3_SHIFT);
	require(pgsize_to_pgshift(123) == -EINVAL);
	require(tbllv_to_pgsize(2) == PTL2_SIZE);
	require(tbllv_to_pgsize(9) == 0);
	require(!pte_is_contiguous(&pte));
	require(!pgsize_is_contiguous(PTL2_SIZE));
	require(!tbllv_to_contpgsize(2));
	require(!tbllv_to_contpgshift(2));
	require(get_contiguous_head(&pte, PTL2_SIZE) == &pte);
	require(get_contiguous_tail(&pte, PTL2_SIZE) == &pte);
	require(!page_is_contiguous_head(&pte, PTL2_SIZE));
	require(!page_is_contiguous_tail(&pte, PTL2_SIZE));
	arch_adjust_allocate_page_size(NULL, 0x4000, &pte, &pgaddr, &pgsize);
	require(pgaddr == (void *)0x1234UL && pgsize == PTL2_SIZE);

	pte_make_null(&pte, PTL2_SIZE);
	require(pte_is_null(&pte));
	mix(&digest, pte);

	printf("pte_helpers ok digest=%016lx pgshift=%d\n",
	       digest, pgsize_to_pgshift(PTL2_SIZE));
	return 0;
}
