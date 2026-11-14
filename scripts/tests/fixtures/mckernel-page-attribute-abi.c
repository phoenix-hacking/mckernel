/* Exercise the real Rust object through the existing x86_64 C ABI. */
#include <ihk/mm.h>

/* Avoid interposing kernel exports such as time on a host libc. */
__asm__(".global _start\n"
	"_start:\n"
	"xor %ebp, %ebp\n"
	"andq $-16, %rsp\n"
	"call main\n"
	"mov %eax, %edi\n"
	"mov $60, %eax\n"
	"syscall\n"
	"ud2\n");

static void puts(const char *message)
{
	unsigned long length = 0;
	long result;
	while (message[length])
		length++;
	__asm__ volatile("syscall" : "=a"(result) : "0"(1L), "D"(1L),
		"S"(message), "d"(length) : "rcx", "r11", "memory");
	__asm__ volatile("syscall" : "=a"(result) : "0"(1L), "D"(1L),
		"S"("\n"), "d"(1L) : "rcx", "r11", "memory");
}
extern unsigned long xpmem_vrflag_to_ptattr_bridge(unsigned long, unsigned long);
extern int xpmem_pt_set_pte_bridge(void *, void *, unsigned long,
		unsigned long, unsigned long);
extern int xpmem_pt_set_range_bridge(void *, void *, unsigned long,
		unsigned long, unsigned long, unsigned long, int, void *, int);

_Static_assert(sizeof(enum ihk_mc_pt_attribute) == 8, "64-bit page attribute ABI");
_Static_assert(PTATTR_NO_EXECUTE == (1UL << 63), "NX occupies bit 63");

static unsigned long expected_attr;
static unsigned long captured_attr;
static int set_count, clear_count, free_count, flush_count, barrier_count;
static int failed_attr, fail_at;
static int allocator;

void *mem_vmap_allocator_bridge(void) { return &allocator; }
unsigned long mem_vmap_alloc_bridge(void *desc, int npages, int align)
{
	(void)desc; (void)npages; (void)align;
	return 0x10000000UL;
}
void mem_vmap_free_bridge(void *desc, unsigned long address, int npages)
{
	(void)desc; (void)address; (void)npages;
	free_count++;
}
int mem_pt_set_page_bridge(page_table_t pt, void *virt, unsigned long phys,
		enum ihk_mc_pt_attribute attr)
{
	int index = set_count++;
	(void)pt; (void)virt; (void)phys;
	failed_attr |= attr != expected_attr;
	return index == fail_at ? -12 : 0;
}
int mem_pt_clear_page_bridge(page_table_t pt, void *virt)
{
	(void)pt; (void)virt;
	clear_count++;
	return 0;
}
void mem_flush_tlb_single_bridge(unsigned long address)
{
	(void)address;
	flush_count++;
}
void mem_barrier_bridge(void) { barrier_count++; }

enum ihk_mc_pt_attribute x86_common_vrflag_to_ptattr_bridge(
		unsigned long flag, unsigned long fault, void *pte)
{
	(void)flag; (void)fault; (void)pte;
	return expected_attr;
}
int ihk_mc_pt_set_pte(page_table_t pt, pte_t *pte, size_t size,
		uintptr_t phys, enum ihk_mc_pt_attribute attr)
{
	(void)pt; (void)pte; (void)size; (void)phys;
	captured_attr = attr;
	return -23;
}
int ihk_mc_pt_set_range(page_table_t pt, struct process_vm *vm, void *start,
		void *end, uintptr_t phys, enum ihk_mc_pt_attribute attr,
		int shift, struct vm_range *range, int overwrite)
{
	(void)pt; (void)vm; (void)start; (void)end; (void)phys;
	(void)shift; (void)range; (void)overwrite;
	captured_attr = attr;
	return -24;
}

static void reset(void)
{
	set_count = clear_count = free_count = flush_count = barrier_count = 0;
	failed_attr = 0;
	fail_at = -1;
}

int main(void)
{
	const unsigned long attrs[] = {
		0, PTATTR_WRITABLE, 1UL << 31, 1UL << 32,
		PTATTR_NO_EXECUTE | PTATTR_WRITABLE, ~0UL,
	};
	int map_failed = 0, xpmem_failed = 0;

	for (unsigned int index = 0; index < sizeof(attrs) / sizeof(attrs[0]); index++) {
		expected_attr = attrs[index];
		reset();
		map_failed |= ihk_mc_map_virtual(0x2345, 3, expected_attr) != (void *)0x10000345;
		map_failed |= failed_attr || set_count != 3 || clear_count || free_count;
		map_failed |= flush_count != 3 || barrier_count != 1;
		ihk_mc_unmap_virtual((void *)0x10000345, 3);
		map_failed |= clear_count != 3 || free_count != 1 || flush_count != 6;

		for (int failure = 0; failure < 3; failure++) {
			reset();
			fail_at = failure;
			map_failed |= ihk_mc_map_virtual(0x2345, 3, expected_attr) != 0;
			map_failed |= failed_attr || set_count != failure + 1;
			map_failed |= clear_count != failure || free_count != 1;
			map_failed |= flush_count != failure || barrier_count;
		}

		xpmem_failed |= xpmem_vrflag_to_ptattr_bridge(0, 0) != expected_attr;
		captured_attr = ~expected_attr;
		xpmem_failed |= xpmem_pt_set_pte_bridge(0, 0, 4096, 0x2000, expected_attr) != -23;
		xpmem_failed |= captured_attr != expected_attr;
		captured_attr = ~expected_attr;
		xpmem_failed |= xpmem_pt_set_range_bridge(0, 0, 0x1000, 0x2000,
			0x3000, expected_attr, 12, 0, 0) != -24;
		xpmem_failed |= captured_attr != expected_attr;
	}
	reset();
	map_failed |= ihk_mc_map_virtual(0, -1, expected_attr) != 0;
	map_failed |= set_count || clear_count || free_count || flush_count || barrier_count;
	puts(map_failed ? "page-map-attribute-abi: FAIL" : "page-map-attribute-abi: PASS");
	puts(xpmem_failed ? "xpmem-attribute-abi: FAIL" : "xpmem-attribute-abi: PASS");
	return map_failed || xpmem_failed;
}
