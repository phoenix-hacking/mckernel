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
extern int printf(const char *, ...);
#define assert(c) do { if (!(c)) return __LINE__; } while (0)
unsigned long recorded[20]; static int body_calls, body_return,callback_calls;
unsigned long mem_tlb_rdtsc_bridge(void) { ++callback_calls; return 0; }
int mem_tlb_current_cpu_bridge(void) { ++callback_calls; return 0; }
int mem_tlb_get_vector_bridge(int type) { ++callback_calls; return 0; }
void mem_tlb_interrupt_cpu_bridge(int cpu, int vector) { ++callback_calls; }
void mem_tlb_noirq_lock_bridge(unsigned long lock_addr) { ++callback_calls; }
void mem_tlb_noirq_unlock_bridge(unsigned long lock_addr) { ++callback_calls; }
void mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value) { ++callback_calls; }
void mem_tlb_atomic_inc_bridge(unsigned long atomic_addr) { ++callback_calls; }
int mem_tlb_atomic_read_bridge(unsigned long atomic_addr) { ++callback_calls; return 0; }
void mem_tlb_flush_single_bridge(unsigned long addr) { ++callback_calls; }
void mem_tlb_flush_all_bridge(void) { ++callback_calls; }
void mem_tlb_pause_bridge(void) { ++callback_calls; }
struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];
const int mem_remote_tlb_geometry[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};
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
		mem_pause_fn_t pause_fn) {
 ++body_calls;
 recorded[0]=(unsigned long)vm;recorded[1]=(unsigned long)addr;
 recorded[2]=(unsigned long)(long)nr_addr;recorded[3]=(unsigned long)(long)cpu_id;
 recorded[4]=(unsigned long)tlb_flush_vector;recorded[5]=(unsigned long)(long)vector_size;
 recorded[6]=(unsigned long)(long)vector_start;recorded[7]=(unsigned long)(long)cpu_set_bits;
 recorded[8]=(unsigned long)rdtsc_fn;
 recorded[9]=(unsigned long)current_cpu_fn;
 recorded[10]=(unsigned long)get_vector_fn;
 recorded[11]=(unsigned long)interrupt_cpu_fn;
 recorded[12]=(unsigned long)lock_fn;
 recorded[13]=(unsigned long)unlock_fn;
 recorded[14]=(unsigned long)atomic_set_fn;
 recorded[15]=(unsigned long)atomic_inc_fn;
 recorded[16]=(unsigned long)atomic_read_fn;
 recorded[17]=(unsigned long)flush_single_fn;
 recorded[18]=(unsigned long)flush_all_fn;
 recorded[19]=(unsigned long)pause_fn;
 return body_return;
}
void original_remote_flush_tlb_array_cpumask(struct process_vm *vm,
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
static struct process_vm vm_storage;
static unsigned long addresses[8]={0,1,4095,4096,~0UL,0x8000000000000000UL,0x12345,0};
int main(void){
 unsigned long saved[20];unsigned long pairs=0;
 int counts[]={-3,-1,0,1,2,8,(-2147483647-1),2147483647};
 int cpus[]={-1,0,1,1023,1024,(-2147483647-1),2147483647};
 int returns[]={(-2147483647-1),-22,-1,0,1,63,64,2147483647};
 for(int v=0;v<2;v++)for(int a=0;a<2;a++)for(unsigned n=0;n<8;n++)for(unsigned cpu=0;cpu<7;cpu++)for(unsigned ret=0;ret<8;ret++){
 struct process_vm *vm=v?&vm_storage:0;unsigned long *addr=a?addresses:0;body_return=returns[ret];
 body_calls=callback_calls=0;memset(recorded,0,sizeof(recorded));
 original_remote_flush_tlb_array_cpumask(vm,addr,counts[n],cpus[cpu]);assert(body_calls==1&&callback_calls==0);memcpy(saved,recorded,sizeof(saved));
 body_calls=callback_calls=0;memset(recorded,0,sizeof(recorded));
 remote_flush_tlb_array_cpumask(vm,addr,counts[n],cpus[cpu]);assert(body_calls==1&&callback_calls==0);assert(memcmp(saved,recorded,sizeof(saved))==0);
 assert(recorded[4]==(unsigned long)tlb_flush_vector);assert(recorded[5]==IHK_TLB_FLUSH_IRQ_VECTOR_SIZE);assert(recorded[6]==IHK_TLB_FLUSH_IRQ_VECTOR_START);assert(recorded[7]==CPU_SETSIZE);
 assert(recorded[8]==(unsigned long)mem_tlb_rdtsc_bridge);
 assert(recorded[9]==(unsigned long)mem_tlb_current_cpu_bridge);
 assert(recorded[10]==(unsigned long)mem_tlb_get_vector_bridge);
 assert(recorded[11]==(unsigned long)mem_tlb_interrupt_cpu_bridge);
 assert(recorded[12]==(unsigned long)mem_tlb_noirq_lock_bridge);
 assert(recorded[13]==(unsigned long)mem_tlb_noirq_unlock_bridge);
 assert(recorded[14]==(unsigned long)mem_tlb_atomic_set_bridge);
 assert(recorded[15]==(unsigned long)mem_tlb_atomic_inc_bridge);
 assert(recorded[16]==(unsigned long)mem_tlb_atomic_read_bridge);
 assert(recorded[17]==(unsigned long)mem_tlb_flush_single_bridge);
 assert(recorded[18]==(unsigned long)mem_tlb_flush_all_bridge);
 assert(recorded[19]==(unsigned long)mem_tlb_pause_bridge);
 ++pairs;
 }
 assert(pairs==1792);printf("PASS actual_original_C_Rust_entry_pairs=%lu full_signature_arguments=20 callback_identities=12 ignored_returns=8 NO_TLB_ALGORITHM_OR_NATIVE_EXECUTION\n",pairs);return 0;
}
