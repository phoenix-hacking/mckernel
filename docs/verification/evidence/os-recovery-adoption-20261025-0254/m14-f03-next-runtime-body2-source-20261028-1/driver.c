/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST initialized-response effect boundary; no offload or host credential calls. */
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

static struct cpu_local_var cpu;
static struct thread thread;
static struct process proc;
static unsigned char expected[sizeof(proc)],saved_thread[sizeof(thread)],saved_cpu[sizeof(cpu)];
static int values[8];
static int response_mode;
static unsigned cpu_calls,cred_calls,sequence,scratch_invalid;
struct cpu_local_var *get_this_cpu_local_var(void)
{
    ++cpu_calls;
    if(sequence!=0)scratch_invalid=1;
    sequence=1;
    return &cpu;
}
int *getcred(int *scratch)
{
    ++cred_calls;
    if(sequence!=1 || !scratch || ((unsigned long)scratch%__alignof__(int)))scratch_invalid=1;
    sequence=2;
    if(response_mode<0)return NULL;
    int *selected=scratch+response_mode;
    for(unsigned i=0;i<8;i++)selected[i]=values[i];
    return selected;
}
extern int syscall_refresh_cred_fields_body_result(void *,int *,size_t,size_t,size_t,size_t,size_t,
                                                  size_t,size_t,size_t,size_t,int *(*)(int *));
#define do_setresuid c_reference_do_setresuid
#include "setresuid-original.C.inc"
#undef do_setresuid
extern void do_setresuid(void);
extern const unsigned long F03_SETRESUID_ABI[15];
extern int puts(const char *);
static int one(unsigned pattern,int state,int mode,int use_rust)
{
    static const unsigned words[]={0,1,0x7fffffffU,0x80000000U,0xffffffffU,0x13579bdfU,0xabcdef01U,0x2468ace0U};
    __builtin_memset(&cpu,0x3c,sizeof cpu);
    __builtin_memset(&thread,0x5a,sizeof thread);
    __builtin_memset(&proc,0xa5,sizeof proc);
    for(unsigned i=0;i<8;i++)__builtin_memcpy(&values[i],&words[(pattern+i)%8],sizeof(int));
    thread.proc=state==2?NULL:&proc;
    cpu.current=state==1?NULL:&thread;
    __builtin_memcpy(expected,&proc,sizeof proc);
    if(state==0 && mode>=0) {
        size_t offsets[]={__builtin_offsetof(struct process,ruid),__builtin_offsetof(struct process,euid),
                          __builtin_offsetof(struct process,suid),__builtin_offsetof(struct process,fsuid)};
        for(unsigned i=0;i<4;i++)__builtin_memcpy(expected+offsets[i],&values[i],sizeof(int));
    }
    __builtin_memcpy(saved_thread,&thread,sizeof thread);
    __builtin_memcpy(saved_cpu,&cpu,sizeof cpu);
    response_mode=mode;cpu_calls=cred_calls=sequence=scratch_invalid=0;
    if(use_rust)do_setresuid();else c_reference_do_setresuid();
    if(cpu_calls!=1 || cred_calls!=(state==1?0:1) || sequence!=(state==1?1:2) || scratch_invalid)return 1;
    if(__builtin_memcmp(expected,&proc,sizeof proc))return 2;
    if(__builtin_memcmp(saved_thread,&thread,sizeof thread) || __builtin_memcmp(saved_cpu,&cpu,sizeof cpu))return 3;
    return 0;
}
int main(void)
{
    unsigned long abi[15]={sizeof(int),__alignof__(int),sizeof(struct thread),__alignof__(struct thread),
        sizeof(struct process),__alignof__(struct process),sizeof(struct cpu_local_var),__alignof__(struct cpu_local_var),
        __builtin_offsetof(struct cpu_local_var,current),__builtin_offsetof(struct thread,proc),
        __builtin_offsetof(struct process,ruid),__builtin_offsetof(struct process,euid),
        __builtin_offsetof(struct process,suid),__builtin_offsetof(struct process,fsuid),sizeof(int[16])};
    if(__builtin_memcmp(abi,F03_SETRESUID_ABI,sizeof abi))return 10;
    unsigned pairs=0;int modes[]={0,8,-1};
    for(unsigned p=0;p<8;p++)for(int state=0;state<3;state++)for(unsigned m=0;m<3;m++) {
        for(int rust=0;rust<2;rust++) {
            int rc=one(p,state,modes[m],rust);
            if(rc)return 20+rc;
        }
        ++pairs;
    }
    if(pairs!=72)return 30;
    puts("PASS setresuid actual-header ABI15; 72 C/Rust pairs; 144 full-process/thread/CPU/provider-order oracles");
    return 0;
}
