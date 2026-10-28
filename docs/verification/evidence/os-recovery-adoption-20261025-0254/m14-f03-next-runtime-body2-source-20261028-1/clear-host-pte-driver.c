/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-only forwarding/log boundaries; no MM, syscall, hardware or guest effects. */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <ihk/debug.h>
#include <ihk/memconst.h>
#include <lwk/stddef.h>

typedef long (*syscall_do_syscall3_fn_t)(int,unsigned long,unsigned long,unsigned long);
typedef void (*clear_host_pte_log_fn_t)(long);
static struct cpu_local_var cpu;
static struct thread thread;
static struct process_vm vm;
static unsigned char saved_cpu[sizeof(cpu)],saved_thread[sizeof(thread)],expected_vm[sizeof(vm)];
static int cpu_id,holding,initial;
static long outcome;
static unsigned cpu_calls,id_calls,forward_calls,log_calls,phase,invalid;
static unsigned long expected_addr,expected_len;

struct cpu_local_var *get_this_cpu_local_var(void)
{
    ++cpu_calls;if(phase!=0)invalid=1;phase=1;return &cpu;
}
int ihk_mc_get_processor_id(void)
{
    ++id_calls;if(phase!=1)invalid=1;phase=2;return cpu_id;
}
int syscall_get_processor_id_bridge(void) { return ihk_mc_get_processor_id(); }
static long syscall_do_syscall3_bridge(int nr,unsigned long addr,unsigned long len,unsigned long arg2)
{
    ++forward_calls;
    if(phase!=2 || nr!=__NR_munmap || addr!=expected_addr || len!=expected_len || arg2!=0)invalid=1;
    if(vm.is_memory_range_lock_taken!=(holding?cpu_id:initial))invalid=1;
    phase=3;return outcome;
}
static void clear_host_pte_log_bridge(long error)
{
    ++log_calls;
    if(phase!=3 || error!=outcome || !error)invalid=1;
    if(vm.is_memory_range_lock_taken!=(holding?-1:initial))invalid=1;
    phase=4;
}
extern long clear_host_pte_body_result(void *,unsigned long,size_t,int,size_t,int,int,
                                     syscall_do_syscall3_fn_t,clear_host_pte_log_fn_t);
#include "clear-host-pte-binding.C.inc"
#define clear_host_pte c_reference_clear_host_pte
#include "clear-host-pte-original.C.inc"
#undef clear_host_pte
extern const unsigned long F03_CLEAR_HOST_PTE_ABI[18];
extern int puts(const char *);

static int one(unsigned long addr,unsigned long len,int hold,int processor,long result,int before,int rust)
{
    __builtin_memset(&cpu,0x3c,sizeof cpu);
    __builtin_memset(&thread,0x5a,sizeof thread);
    __builtin_memset(&vm,0xa5,sizeof vm);
    cpu.current=&thread;thread.vm=&vm;vm.is_memory_range_lock_taken=before;
    __builtin_memcpy(saved_cpu,&cpu,sizeof cpu);__builtin_memcpy(saved_thread,&thread,sizeof thread);
    __builtin_memcpy(expected_vm,&vm,sizeof vm);
    if(hold) {
        int restored=-1;
        __builtin_memcpy(expected_vm+__builtin_offsetof(struct process_vm,is_memory_range_lock_taken),&restored,sizeof restored);
    }
    expected_addr=addr;expected_len=len;holding=hold;cpu_id=processor;outcome=result;initial=before;
    cpu_calls=id_calls=forward_calls=log_calls=phase=invalid=0;
    long observed=rust?clear_host_pte(addr,len,hold):c_reference_clear_host_pte(addr,len,hold);
    if(observed!=result || cpu_calls!=1 || id_calls!=1 || forward_calls!=1 || log_calls!=(result!=0))return 1;
    if(invalid || phase!=(result?4:3))return 2;
    if(__builtin_memcmp(expected_vm,&vm,sizeof vm))return 3;
    if(__builtin_memcmp(saved_cpu,&cpu,sizeof cpu) || __builtin_memcmp(saved_thread,&thread,sizeof thread))return 4;
    return 0;
}

int main(void)
{
    unsigned long abi[18]={sizeof(struct thread),__alignof__(struct thread),sizeof(struct process_vm),__alignof__(struct process_vm),
        sizeof(struct cpu_local_var),__alignof__(struct cpu_local_var),__builtin_offsetof(struct cpu_local_var,current),
        __builtin_offsetof(struct thread,vm),__builtin_offsetof(struct process_vm,is_memory_range_lock_taken),
        sizeof(struct f03_clear_host_pte_binding),__alignof__(struct f03_clear_host_pte_binding),
        __builtin_offsetof(struct f03_clear_host_pte_binding,munmap_nr),__builtin_offsetof(struct f03_clear_host_pte_binding,forward),
        __builtin_offsetof(struct f03_clear_host_pte_binding,log),sizeof(int),sizeof(syscall_do_syscall3_fn_t),
        sizeof(clear_host_pte_log_fn_t),sizeof(uintptr_t)};
    if(__builtin_memcmp(abi,F03_CLEAR_HOST_PTE_ABI,sizeof abi))return 10;
    const unsigned long words[]={0,1,0x7fffffffUL,0x80000000UL,0xffffffffUL,0x100000000UL,0x8000000000000000UL,~0UL};
    const int holds[]={-1,0,1,2},ids[]={-1,0,7,0x7fffffff},initials[]={-1,0,13};
    const long results[]={0,-1,-12,1,(-0x7fffffffffffffffL-1),0x7fffffffffffffffL};
    unsigned pairs=0;
    for(unsigned a=0;a<8;a++)for(unsigned h=0;h<4;h++)for(unsigned c=0;c<4;c++)for(unsigned r=0;r<6;r++)for(unsigned i=0;i<3;i++) {
        for(int rust=0;rust<2;rust++) {
            int rc=one(words[a],words[(a+3)%8],holds[h],ids[c],results[r],initials[i],rust);
            if(rc)return 20+rc;
        }
        ++pairs;
    }
    if(pairs!=2304)return 30;
    puts("PASS clear-host-pte actual-header ABI18; 2304 C/Rust pairs; 4608 exact-forward/publication/restoration/log/full-state oracles");
    return 0;
}
