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
extern const int mem_remote_tlb_geometry[3];
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(mem_remote_tlb_geometry),const int[3]),"immutable C int geometry ABI");
_Static_assert(sizeof(int)==4&&_Alignof(int)==4&&sizeof(unsigned long)==8,"actual x86_64 scalar ABI");
const unsigned long M14_C_TLB_LAYOUT[15]={
 sizeof(int),_Alignof(int),sizeof(unsigned long),sizeof(struct process_vm*),
 sizeof(const int[3]),_Alignof(const int[3]),sizeof(struct tlb_flush_entry),_Alignof(struct tlb_flush_entry),
 __builtin_offsetof(struct tlb_flush_entry,vm),__builtin_offsetof(struct tlb_flush_entry,addr),
 __builtin_offsetof(struct tlb_flush_entry,nr_addr),__builtin_offsetof(struct tlb_flush_entry,pending),
 __builtin_offsetof(struct tlb_flush_entry,lock),CPU_SETSIZE,sizeof(mem_rdtsc_fn_t)};
const int M14_C_TLB_GEOMETRY[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};
unsigned long mem_tlb_rdtsc_bridge(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_rdtsc_bridge),mem_rdtsc_fn_t),"mem_tlb_rdtsc_bridge ABI");
int mem_tlb_current_cpu_bridge(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_current_cpu_bridge),mem_current_cpu_fn_t),"mem_tlb_current_cpu_bridge ABI");
int mem_tlb_get_vector_bridge(int type);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_get_vector_bridge),mem_get_vector_fn_t),"mem_tlb_get_vector_bridge ABI");
void mem_tlb_interrupt_cpu_bridge(int cpu, int vector);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_interrupt_cpu_bridge),mem_interrupt_cpu_fn_t),"mem_tlb_interrupt_cpu_bridge ABI");
void mem_tlb_noirq_lock_bridge(unsigned long lock_addr);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_noirq_lock_bridge),mem_noirq_lock_fn_t),"mem_tlb_noirq_lock_bridge ABI");
void mem_tlb_noirq_unlock_bridge(unsigned long lock_addr);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_noirq_unlock_bridge),mem_noirq_lock_fn_t),"mem_tlb_noirq_unlock_bridge ABI");
void mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_set_bridge),mem_atomic_set_fn_t),"mem_tlb_atomic_set_bridge ABI");
void mem_tlb_atomic_inc_bridge(unsigned long atomic_addr);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_inc_bridge),mem_atomic_inc_fn_t),"mem_tlb_atomic_inc_bridge ABI");
int mem_tlb_atomic_read_bridge(unsigned long atomic_addr);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_read_bridge),mem_atomic_read_fn_t),"mem_tlb_atomic_read_bridge ABI");
void mem_tlb_flush_single_bridge(unsigned long addr);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_flush_single_bridge),mem_flush_tlb_single_fn_t),"mem_tlb_flush_single_bridge ABI");
void mem_tlb_flush_all_bridge(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_flush_all_bridge),mem_flush_tlb_all_fn_t),"mem_tlb_flush_all_bridge ABI");
void mem_tlb_pause_bridge(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_pause_bridge),mem_pause_fn_t),"mem_tlb_pause_bridge ABI");
