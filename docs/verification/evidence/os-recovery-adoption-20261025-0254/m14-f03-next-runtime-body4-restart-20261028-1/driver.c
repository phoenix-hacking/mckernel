/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-only exact print events and controlled logger mutations; no OS effects. */
#include <types.h>
#include <kmsg.h>
#include <stdarg.h>
#include "uti.h"

unsigned long uti_desc;
static struct uti_desc primary,decoy;
static unsigned char expected_primary[sizeof primary],saved_decoy[sizeof decoy];
struct event { int kind,index;long count; };
static struct event expected[1026];
static unsigned expected_count,observed_count,invalid,section;
static int mutation,log_result;
static long emit_counts[2][512];

int kprintf(const char *format,...)
{
    struct event actual={0,0,0};
    va_list args;va_start(args,format);
    if(!__builtin_strcmp(format,"Syscall stats for offloaded thread:\n"))actual.kind=1;
    else if(!__builtin_strcmp(format,"Syscall stats for other threads:\n"))actual.kind=2;
    else if(!__builtin_strcmp(format,"nr=%d #called=%ld\n")) {
        actual.kind=3;actual.index=va_arg(args,int);actual.count=va_arg(args,long);
    }
    else invalid=1;
    va_end(args);
    if(observed_count>=expected_count)invalid=1;
    else {
        const struct event *want=&expected[observed_count];
        if(actual.kind!=want->kind || actual.index!=want->index || actual.count!=want->count)invalid=1;
    }
    ++observed_count;
    if(actual.kind==1) {
        section=0;
        /* The production entry must keep the descriptor captured before log. */
        uti_desc=(unsigned long)&decoy;
        if(mutation) {
            primary.syscalls[0]=-9;
            primary.syscalls[511]=(-0x7fffffffffffffffL-1);
        }
        if(mutation==2)primary.syscalls[255]=17;
    }
    else if(actual.kind==2) {
        section=1;
        if(mutation) {
            primary.syscalls2[0]=0x100000000L;
            primary.syscalls2[511]=-17;
        }
    }
    else if(actual.kind==3 && section==0 && mutation && actual.index==0) {
        primary.syscalls[1]=0x7fffffffffffffffL;
    }
    else if(actual.kind==3 && section==0 && mutation==2 && actual.index==255) {
        primary.syscalls[0]=123; /* Already visited: never printed again. */
        primary.syscalls[256]=-77;
    }
    return log_result; /* Both implementations must ignore logger failures. */
}

#define util_show_syscall_profile c_reference_util_show_syscall_profile
#include "util-profile-original.C.inc"
#undef util_show_syscall_profile
extern int util_show_syscall_profile(void);
extern const unsigned long F03_UTIL_PROFILE_ABI[26];
extern int puts(const char *);

static long value(unsigned pattern,unsigned section_id,unsigned i)
{
    const long edges[]={0,1,-1,(-0x7fffffffffffffffL-1),0x7fffffffffffffffL,0x100000000L};
    switch(pattern) {
    case 0:return 0;
    case 1:return i<6?edges[(i+section_id)%6]:0;
    case 2:return i==511?edges[section_id?3:4]:0;
    case 3:return (i&1)?0:((section_id?-1L:1L)*((long)i+1));
    case 4:return (i&1)?-((long)i+0x100000000L):((long)i+0x100000000L);
    default:return edges[(i*5+section_id*3)%6];
    }
}

static void apply_expected_mutations(struct uti_desc *final)
{
    if(!mutation)return;
    emit_counts[0][0]=final->syscalls[0]=-9;
    emit_counts[0][511]=final->syscalls[511]=(-0x7fffffffffffffffL-1);
    emit_counts[0][1]=final->syscalls[1]=0x7fffffffffffffffL;
    emit_counts[1][0]=final->syscalls2[0]=0x100000000L;
    emit_counts[1][511]=final->syscalls2[511]=-17;
    if(mutation==2) {
        emit_counts[0][255]=final->syscalls[255]=17;
        emit_counts[0][256]=final->syscalls[256]=-77;
        final->syscalls[0]=123;
    }
}

static int one(unsigned pattern,int mode,int logger_result,int rust)
{
    __builtin_memset(&primary,0xa5,sizeof primary);__builtin_memset(&decoy,0x6b,sizeof decoy);
    for(unsigned s=0;s<2;s++)for(unsigned i=0;i<512;i++) {
        long count=value(pattern,s,i);
        if(s)primary.syscalls2[i]=count;else primary.syscalls[i]=count;
        emit_counts[s][i]=count;
    }
    __builtin_memcpy(saved_decoy,&decoy,sizeof decoy);
    struct uti_desc final=primary;
    mutation=mode;log_result=logger_result;
    apply_expected_mutations(&final);
    __builtin_memcpy(expected_primary,&final,sizeof final);
    expected_count=observed_count=invalid=section=0;
    for(unsigned s=0;s<2;s++) {
        expected[expected_count++]=(struct event){.kind=(int)s+1};
        for(unsigned i=0;i<512;i++)if(emit_counts[s][i])
            expected[expected_count++]=(struct event){.kind=3,.index=(int)i,.count=emit_counts[s][i]};
    }
    uti_desc=(unsigned long)&primary;
    int result=rust?util_show_syscall_profile():c_reference_util_show_syscall_profile();
    if(result || invalid || observed_count!=expected_count)return 1;
    if(uti_desc!=(unsigned long)&decoy)return 2;
    if(__builtin_memcmp(&primary,expected_primary,sizeof primary) || __builtin_memcmp(&decoy,saved_decoy,sizeof decoy))return 3;
    return 0;
}

int main(void)
{
    unsigned long abi[26]={
        sizeof(struct syscall_struct),__alignof__(struct syscall_struct),
        __builtin_offsetof(struct syscall_struct,number),__builtin_offsetof(struct syscall_struct,args),
        __builtin_offsetof(struct syscall_struct,ret),__builtin_offsetof(struct syscall_struct,uti_info),
        sizeof(struct uti_desc),__alignof__(struct uti_desc),
        __builtin_offsetof(struct uti_desc,lctx),__builtin_offsetof(struct uti_desc,rctx),
        __builtin_offsetof(struct uti_desc,mck_tid),__builtin_offsetof(struct uti_desc,key),
        __builtin_offsetof(struct uti_desc,pid),__builtin_offsetof(struct uti_desc,tid),
        __builtin_offsetof(struct uti_desc,uti_info),__builtin_offsetof(struct uti_desc,fd),
        __builtin_offsetof(struct uti_desc,syscall_stack),__builtin_offsetof(struct uti_desc,syscall_stack_top),
        __builtin_offsetof(struct uti_desc,syscalls),__builtin_offsetof(struct uti_desc,syscalls2),
        __builtin_offsetof(struct uti_desc,start_syscall_intercept),UTI_SZ_SYSCALL_STACK,
        sizeof(((struct uti_desc *)0)->syscalls)/sizeof(long),sizeof(int),sizeof(long),sizeof(unsigned long)};
    if(__builtin_memcmp(abi,F03_UTIL_PROFILE_ABI,sizeof abi))return 10;
    const int returns[]={0,-5,(-0x7fffffff-1),0x7fffffff};
    unsigned pairs=0;
    for(unsigned pattern=0;pattern<6;pattern++)for(int mode=0;mode<3;mode++)for(unsigned r=0;r<4;r++) {
        for(int rust=0;rust<2;rust++) {
            int rc=one(pattern,mode,returns[r],rust);
            if(rc)return 20+rc;
        }
        ++pairs;
    }
    if(pairs!=72)return 30;
    puts("PASS util-profile genuine-header ABI26; 72 C/Rust pairs; exact ordered varargs, signed counts, live reads, descriptor snapshot and full-state oracles");
    return 0;
}
