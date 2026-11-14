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
