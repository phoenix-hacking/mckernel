/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <kmsg.h>
#include <kmalloc.h>
#include <string.h>
#include <ihk/cpu.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <ihk/page_alloc.h>
#include <registers.h>
#ifdef ATTACHED_MIC
#include <sysdeps/mic/mic/micconst.h>
#include <sysdeps/mic/mic/micsboxdefine.h>
#endif
#include <cls.h>
#include <page.h>
#include <kref.h>
#include <bitops.h>
#include <cpulocal.h>
#include <init.h>
#include <cas.h>
#include <rusage_private.h>
#include <syscall.h>
#include <profile.h>
#include <process.h>
#include <limits.h>
#include <sysfs.h>
#include <ihk/debug.h>
#include <llist.h>
#include <bootparam.h>
#include <memobj.h>

//#define DEBUG_PRINT_MEM

#ifdef DEBUG_PRINT_MEM
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

typedef unsigned long (*mem_rdtsc_fn_t)(void);
typedef int (*mem_current_cpu_fn_t)(void);
typedef int (*mem_get_vector_fn_t)(int type);
typedef void (*mem_interrupt_cpu_fn_t)(int cpu, int vector);
typedef void (*mem_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*mem_atomic_set_fn_t)(unsigned long atomic_addr, int value);
typedef void (*mem_atomic_inc_fn_t)(unsigned long atomic_addr);
typedef int (*mem_atomic_read_fn_t)(unsigned long atomic_addr);
typedef void (*mem_flush_tlb_single_fn_t)(unsigned long addr);
typedef void (*mem_flush_tlb_all_fn_t)(void);
typedef void (*mem_pause_fn_t)(void);
int mem_remote_flush_tlb_array_body_result(
		struct process_vm *vm, unsigned long *addr, int nr_addr,
		int cpu_id, struct tlb_flush_entry *tlb_flush_vector,
		int vector_size, int vector_start, int cpu_set_bits,
		mem_rdtsc_fn_t rdtsc_fn,
		mem_current_cpu_fn_t current_cpu_fn,
		mem_get_vector_fn_t get_vector_fn,
		mem_interrupt_cpu_fn_t interrupt_cpu_fn,
		mem_noirq_lock_fn_t lock_fn,
		mem_noirq_lock_fn_t unlock_fn,
		mem_atomic_set_fn_t atomic_set_fn,
		mem_atomic_inc_fn_t atomic_inc_fn,
		mem_atomic_read_fn_t atomic_read_fn,
		mem_flush_tlb_single_fn_t flush_single_fn,
		mem_flush_tlb_all_fn_t flush_all_fn,
		mem_pause_fn_t pause_fn);
struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];

/* Immutable source-header geometry; no new C runtime implementation. */
#ifdef MCKERNEL_RUST_MEM_HELPERS
const int mem_remote_tlb_geometry[3] = {
	IHK_TLB_FLUSH_IRQ_VECTOR_SIZE, IHK_TLB_FLUSH_IRQ_VECTOR_START, CPU_SETSIZE
};
#define MEM_TLB_PUBLIC_BRIDGE
#else
#define MEM_TLB_PUBLIC_BRIDGE static
#endif

MEM_TLB_PUBLIC_BRIDGE unsigned long mem_tlb_rdtsc_bridge(void)
{
	return rdtsc();
}

MEM_TLB_PUBLIC_BRIDGE int mem_tlb_current_cpu_bridge(void)
{
	return ihk_mc_get_processor_id();
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value)
{
	ihk_atomic_set((ihk_atomic_t *)atomic_addr, value);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_atomic_inc_bridge(unsigned long atomic_addr)
{
	ihk_atomic_inc((ihk_atomic_t *)atomic_addr);
}

static void mem_tlb_atomic_dec_bridge(unsigned long atomic_addr)
{
	ihk_atomic_dec((ihk_atomic_t *)atomic_addr);
}

MEM_TLB_PUBLIC_BRIDGE int mem_tlb_atomic_read_bridge(unsigned long atomic_addr)
{
	return ihk_atomic_read((ihk_atomic_t *)atomic_addr);
}

MEM_TLB_PUBLIC_BRIDGE int mem_tlb_get_vector_bridge(int type)
{
	return ihk_mc_get_vector(type);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_interrupt_cpu_bridge(int cpu, int vector)
{
	ihk_mc_interrupt_cpu(cpu, vector);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_flush_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_flush_all_bridge(void)
{
	flush_tlb();
}

MEM_TLB_PUBLIC_BRIDGE void mem_tlb_pause_bridge(void)
{
	cpu_pause();
}

#undef MEM_TLB_PUBLIC_BRIDGE

void remote_flush_tlb_cpumask(struct process_vm *vm,
		unsigned long addr, int cpu_id)
{
	unsigned long __addr = addr;
	return remote_flush_tlb_array_cpumask(vm, &__addr, 1, cpu_id);
}

#ifndef MCKERNEL_RUST_MEM_HELPERS
void remote_flush_tlb_array_cpumask(struct process_vm *vm,
		unsigned long *addr,
		int nr_addr,
		int cpu_id)
{
	(void)mem_remote_flush_tlb_array_body_result(vm, addr, nr_addr, cpu_id,
			tlb_flush_vector, IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,
			IHK_TLB_FLUSH_IRQ_VECTOR_START, CPU_SETSIZE,
			mem_tlb_rdtsc_bridge, mem_tlb_current_cpu_bridge,
			mem_tlb_get_vector_bridge, mem_tlb_interrupt_cpu_bridge,
			mem_tlb_noirq_lock_bridge, mem_tlb_noirq_unlock_bridge,
			mem_tlb_atomic_set_bridge, mem_tlb_atomic_inc_bridge,
			mem_tlb_atomic_read_bridge, mem_tlb_flush_single_bridge,
			mem_tlb_flush_all_bridge, mem_tlb_pause_bridge);
}
#endif /* C fallback; default Rust entry owns this symbol. */

