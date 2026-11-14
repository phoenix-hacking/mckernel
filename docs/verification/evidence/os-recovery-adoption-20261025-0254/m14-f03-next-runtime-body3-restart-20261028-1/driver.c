/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST fixture only: mock range/host callbacks, no actual MM or syscall effects. */
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
#include <mman.h>

#include "do-munmap-types.C.inc"
static struct cpu_local_var cpu;
static struct thread thread;
static struct process_vm vm;
static struct process proc;
static unsigned char saved_cpu[sizeof cpu], saved_thread[sizeof thread];
static unsigned char saved_vm[sizeof vm], expected_proc[sizeof proc];
static unsigned cpu_calls,begin_calls,remove_calls,clear_calls,set_calls,finish_calls,log_calls,phase,invalid;
static unsigned long expected_addr,expected_len,after_va,after_len;
static int hold,remove_result,ro_result,set_result,expected_result,expected_host;
static long clear_result;

struct cpu_local_var *get_this_cpu_local_var(void)
{
    ++cpu_calls;if(phase!=0)invalid=1;phase=1;return &cpu;
}
static void do_munmap_begin_bridge(void)
{
    ++begin_calls;if(phase!=1)invalid=1;phase=2;
}
static int do_munmap_remove_range_bridge(void *v,unsigned long start,unsigned long end,int *ro)
{
    ++remove_calls;
    if(phase!=2 || v!=&vm || start!=expected_addr || end!=expected_addr+expected_len || *ro!=0)invalid=1;
    *ro=ro_result;
    /* Observe that the Rust body reads straight-map fields AFTER removal. */
    proc.straight_va=(void *)after_va;proc.straight_len=after_len;
    phase=3;return remove_result;
}
static long do_munmap_clear_host_bridge(unsigned long addr,size_t len,int holding)
{
    ++clear_calls;
    if(phase!=3 || expected_host!=1 || addr!=expected_addr || len!=expected_len || holding!=hold)invalid=1;
    phase=4;return clear_result;
}
static int do_munmap_set_host_bridge(unsigned long addr,size_t len,int prot,int holding)
{
    ++set_calls;
    if(phase!=3 || expected_host!=2 || addr!=expected_addr || len!=expected_len || holding!=hold || prot!=(PROT_READ|PROT_WRITE|PROT_EXEC))invalid=1;
    phase=4;return set_result;
}
static void do_munmap_finish_bridge(void)
{
    ++finish_calls;if(phase!=(expected_host?4:3))invalid=1;phase=5;
}
static void do_munmap_log_bridge(unsigned long addr,size_t len,int error)
{
    ++log_calls;if(phase!=5 || addr!=expected_addr || len!=expected_len || error!=expected_result)invalid=1;phase=6;
}
#include "do-munmap-binding.C.inc"
#include "syscall-offset-ptr.original.C.inc"
#define do_munmap_body_result c_reference_do_munmap_body_result
static int
#include "do-munmap-body.original.C.inc"
#define do_munmap c_reference_do_munmap
#include "do-munmap-original.C.inc"
#undef do_munmap
#undef do_munmap_body_result
extern const unsigned long F03_DO_MUNMAP_ABI[27];
extern int puts(const char *);

struct scenario { unsigned long addr,len,before_va,before_len,after_va,after_len; };
static int one(const struct scenario *s,int holding,int rr,int ro,long cr,int sr,int rust)
{
    __builtin_memset(&cpu,0x3c,sizeof cpu);__builtin_memset(&thread,0x5a,sizeof thread);
    __builtin_memset(&vm,0xa5,sizeof vm);__builtin_memset(&proc,0x6b,sizeof proc);
    cpu.current=&thread;thread.vm=&vm;thread.proc=&proc;
    proc.straight_va=(void *)s->before_va;proc.straight_len=s->before_len;
    __builtin_memcpy(saved_cpu,&cpu,sizeof cpu);__builtin_memcpy(saved_thread,&thread,sizeof thread);
    __builtin_memcpy(saved_vm,&vm,sizeof vm);__builtin_memcpy(expected_proc,&proc,sizeof proc);
    void *after_ptr=(void *)s->after_va;
    __builtin_memcpy(expected_proc+__builtin_offsetof(struct process,straight_va),&after_ptr,sizeof after_ptr);
    __builtin_memcpy(expected_proc+__builtin_offsetof(struct process,straight_len),&s->after_len,sizeof s->after_len);
    expected_addr=s->addr;expected_len=s->len;after_va=s->after_va;after_len=s->after_len;
    hold=holding;remove_result=rr;ro_result=ro;clear_result=cr;set_result=sr;
    /* Independent expected behavior, not C/Rust mutual equality alone. */
    int outside=!after_va || expected_addr<after_va || expected_addr+expected_len>after_va+after_len;
    expected_host=outside?((rr || !ro)?1:2):0;
    expected_result=rr;
    if(expected_host==1 && !rr)expected_result=(int)cr;
    if(expected_host==2)expected_result=sr;
    cpu_calls=begin_calls=remove_calls=clear_calls=set_calls=finish_calls=log_calls=phase=invalid=0;
    int observed=rust?do_munmap((void *)s->addr,s->len,holding):c_reference_do_munmap((void *)s->addr,s->len,holding);
    if(observed!=expected_result || cpu_calls!=1 || begin_calls!=1 || remove_calls!=1 || finish_calls!=1 || log_calls!=1)return 1;
    if(clear_calls!=(expected_host==1) || set_calls!=(expected_host==2) || invalid || phase!=6)return 2;
    if(__builtin_memcmp(saved_cpu,&cpu,sizeof cpu) || __builtin_memcmp(saved_thread,&thread,sizeof thread))return 3;
    if(__builtin_memcmp(saved_vm,&vm,sizeof vm) || __builtin_memcmp(expected_proc,&proc,sizeof proc))return 4;
    return 0;
}

int main(void)
{
    unsigned long abi[27]={
        sizeof(struct thread),__alignof__(struct thread),sizeof(struct process_vm),__alignof__(struct process_vm),
        sizeof(struct process),__alignof__(struct process),sizeof(struct cpu_local_var),__alignof__(struct cpu_local_var),
        __builtin_offsetof(struct cpu_local_var,current),__builtin_offsetof(struct thread,vm),__builtin_offsetof(struct thread,proc),
        __builtin_offsetof(struct process,straight_va),__builtin_offsetof(struct process,straight_len),
        sizeof(struct f03_do_munmap_binding),__alignof__(struct f03_do_munmap_binding),
        __builtin_offsetof(struct f03_do_munmap_binding,begin),__builtin_offsetof(struct f03_do_munmap_binding,remove_range),
        __builtin_offsetof(struct f03_do_munmap_binding,clear_host),__builtin_offsetof(struct f03_do_munmap_binding,set_host),
        __builtin_offsetof(struct f03_do_munmap_binding,finish),__builtin_offsetof(struct f03_do_munmap_binding,log),
        sizeof(int),sizeof(long),sizeof(size_t),sizeof(do_munmap_clear_host_fn_t),
        sizeof(do_munmap_remove_range_fn_t),PROT_READ|PROT_WRITE|PROT_EXEC};
    if(__builtin_memcmp(abi,F03_DO_MUNMAP_ABI,sizeof abi))return 10;
    const struct scenario cases[]={
        {0,0,0,0,0,0},
        {0x1000,0x1000,0,0,0,0},
        {0x1000,0x1000,0x1000,0x1000,0x1000,0x1000},
        {0x1800,0x100,0x1000,0x1000,0x1000,0x1000},
        {0xfff,1,0x1000,0x1000,0x1000,0x1000},
        {0x1fff,2,0x1000,0x1000,0x1000,0x1000},
        {~0UL-0x10,0x20,0,0,0,0},
        {~0UL-0x10,0x20,~0UL-0x20,0x100,~0UL-0x20,0x100},
        {0x2000,0,0x1000,0x1000,0x1000,0x1000},
        {0x8000000000000000UL,0x100000000UL,0x8000000000000000UL,0x100000001UL,0x8000000000000000UL,0x100000001UL},
        {0x1800,0x100,0,0,0x1000,0x1000},
        {0x1800,0x100,0x1000,0x1000,0,0},
    };
    const int holds[]={-1,0,1},removes[]={0,-12,17},ros[]={0,1,-1},sets[]={0,-22,9};
    const long clears[]={0,-1,1,(-0x7fffffffffffffffL-1),0x7fffffffffffffffL};
    unsigned pairs=0;
    for(unsigned a=0;a<12;a++)for(unsigned h=0;h<3;h++)for(unsigned r=0;r<3;r++)for(unsigned o=0;o<3;o++)for(unsigned c=0;c<5;c++)for(unsigned t=0;t<3;t++) {
        for(int rust=0;rust<2;rust++) {
            int rc=one(&cases[a],holds[h],removes[r],ros[o],clears[c],sets[t],rust);
            if(rc)return 20+rc;
        }
        ++pairs;
    }
    if(pairs!=4860)return 30;
    puts("PASS do-munmap actual-header ABI27; 4860 C/Rust pairs; 9720 independent order/error/straight-map/full-state oracles");
    return 0;
}
