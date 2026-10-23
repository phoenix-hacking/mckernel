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

extern int printf(const char *, ...);
#define CHECK(c) do { if (!(c)) return __LINE__; } while (0)
struct snapshot {
    struct process_vm *vm;
    unsigned long value;
    int nr;
    int cpu;
    int aligned;
};
static struct snapshot seen;
static int calls, invalid, mutate;
static struct process_vm vm_storage;
/* Recorder reads only the initialized local while the actual caller is active.
 * It never dereferences vm or saves the pointer for use after caller return. */
void remote_flush_tlb_array_cpumask(struct process_vm *vm,
        unsigned long *addr, int nr_addr, int cpu_id)
{
    ++calls;
    if (!addr || nr_addr != 1) { invalid=1; return; }
    seen.vm=vm;seen.value=*addr;seen.nr=nr_addr;seen.cpu=cpu_id;
    seen.aligned=((unsigned long)addr % _Alignof(unsigned long))==0;
    if (mutate) *addr=~*addr; /* valid mutable-pointer fixture boundary case */
}
void original_remote_flush_tlb_cpumask(struct process_vm *vm,
		unsigned long addr, int cpu_id)
{
	unsigned long __addr = addr;
	return remote_flush_tlb_array_cpumask(vm, &__addr, 1, cpu_id);
}
int main(void)
{
    unsigned long values[136]={0,1,4095,4096,~0UL,0x8000000000000000UL,0x12345,0xaaaaaaaaaaaaaaaaUL};
    int cpus[9]={-1,0,1,63,64,1023,1024,(-2147483647-1),2147483647};
    for (unsigned i=0;i<64;++i) { values[8+2*i]=1UL<<i;values[9+2*i]=~(1UL<<i); }
    unsigned long pairs=0;
    for(int v=0;v<2;++v)for(unsigned a=0;a<136;++a)for(unsigned cpu=0;cpu<9;++cpu)for(int m=0;m<2;++m){
        struct process_vm *vm=v?&vm_storage:0;
        unsigned long input=values[a], original_input=input;
        mutate=m;calls=invalid=0;
        original_remote_flush_tlb_cpumask(vm,input,cpus[cpu]);
        CHECK(calls==1 && !invalid && input==original_input);
        struct snapshot old=seen;
        calls=invalid=0;
        remote_flush_tlb_cpumask(vm,input,cpus[cpu]);
        CHECK(calls==1 && !invalid && input==original_input);
        CHECK(old.vm==seen.vm && old.value==seen.value && old.nr==seen.nr && old.cpu==seen.cpu && old.aligned==seen.aligned);
        CHECK(seen.vm==vm && seen.value==input && seen.nr==1 && seen.cpu==cpus[cpu] && seen.aligned);
        ++pairs;
    }
    CHECK(pairs==4896);
    printf("PASS actual_original_C_Rust_single_entry_pairs=%lu caller_args=3 callee_args=4 one_call=1 initialized_local_lifetime=1 caller_value_preserved=1 NO_TLB_IRQ_OR_NATIVE_EXECUTION\n",pairs);
    return 0;
}
