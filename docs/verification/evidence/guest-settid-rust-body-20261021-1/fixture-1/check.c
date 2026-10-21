#include "fixture.h"

struct vector {
    int count, null_tids;
    long returned;
    int narrowed;
};
static const struct vector cases[] = {
    {1024,0,37,37}, {0,1,0,0}, {-1,0,-1,-1},
    {INT_MIN,1,INT_MIN,INT_MIN}, {INT_MAX,0,INT_MAX,INT_MAX},
    {1,1,4294967295L,-1}, {0,0,4294967296L,0},
    {-1,1,4294967333L,37}, {1,0,-4294967296L,0},
    {2,0,2147483648L,INT_MIN}, {0,1,-2147483649L,INT_MAX},
    {1024,0,LONG_MIN,0}
};
struct observation {
    unsigned char bytes[72];
    char trace[5], log[128];
    int result, translations, cpus, calls, logs;
};
static struct observation observed;
static const struct vector *current;
static unsigned case_index, stage;
static int candidate_mode, expected_cpu;
static int *expected_tids;
static struct syscall_request *carrier;
static unsigned long expected_pa;

static void require(int ok, const char *reason)
{
    if (!ok) {
        fprintf(stderr,"case=%u mode=%s stage=%u: %s\n",
                case_index,candidate_mode?"Rust":"C",stage,reason);
        exit(1);
    }
}
static void event(char value, unsigned expected)
{
    require(stage==expected,"callback order");
    require(stage<4,"callback count bound");
    observed.trace[stage++]=value;
}
unsigned long fixture_virt_to_phys(void *ptr)
{
    event('V',0);
    require(ptr==expected_tids,"translation argument, including NULL");
    ++observed.translations;
    return expected_pa;
}
int fixture_get_cpu(void)
{
    event('C',1);
    ++observed.cpus;
    return expected_cpu;
}
long fixture_do_syscall(struct syscall_request *request, int cpu)
{
    unsigned char expected[72]={0};
    uint64_t number=186;
    uint64_t count=(uint64_t)(int64_t)current->count;
    event('D',2);
    require(cpu==expected_cpu,"CPU callback result passed to offload");
    require(request!=NULL,"request address");
    require((uintptr_t)request%_Alignof(struct syscall_request)==0,"request alignment");
    if (candidate_mode)
        require(request==carrier,"same invocation Ccarrier passed to offload");
    /* Fixed authoritative byte offsets form an oracle independent of setters. */
    memcpy(expected+16,&number,8);
    memcpy(expected+56,&count,8);
    memcpy(expected+64,&expected_pa,8);
    memcpy(observed.bytes,request,72);
    require(memcmp(expected,observed.bytes,72)==0,"full request zeroing/field bytes");
    ++observed.calls;
    return current->returned;
}
int fixture_kprintf(const char *format,...)
{
    va_list ap;
    int result;
    event('L',3);
    require(current->narrowed<0,"log only for narrowed negative result");
    va_start(ap,format);
    result=vsnprintf(observed.log,sizeof(observed.log),format,ap);
    va_end(ap);
    require(result>0 && (size_t)result<sizeof(observed.log),"complete log bytes");
    ++observed.logs;
    return result;
}

extern int __real_syscall_settid_body_result(struct syscall_request *,int,int *,int,
        syscall_virt_to_phys_fn_t,syscall_get_cpu_fn_t,
        syscall_request_call_fn_t,void (*)(int));

/* Fixture-only GNU ld wrapper. The actual C adapter and Rust body stay intact. */
int __wrap_syscall_settid_body_result(struct syscall_request *request,int count,
        int *tids,int nr,syscall_virt_to_phys_fn_t virt,
        syscall_get_cpu_fn_t cpu,syscall_request_call_fn_t call,void (*log)(int))
{
    require(candidate_mode && stage==0 && carrier==NULL,"one Rust body entry");
    carrier=request;
    memset(request,0xa5,sizeof(*request));
    return __real_syscall_settid_body_result(request,count,tids,nr,virt,cpu,call,log);
}

static struct observation run(int mode, int *tids)
{
    char expected_log[128]={0};
    memset(&observed,0,sizeof(observed));
    candidate_mode=mode;
    carrier=NULL;
    stage=0;
    expected_tids=current->null_tids?NULL:tids;
    expected_cpu=case_index%2?7:0;
    expected_pa=0xfedcba9876543000UL+case_index;
    observed.result=mode?run_candidate(current->count,expected_tids):
                         run_original(current->count,expected_tids);
    require(observed.result==current->narrowed,"independent narrowed result");
    require(observed.translations==1 && observed.cpus==1 && observed.calls==1,
            "exactly one translation, CPU query and offload");
    require(observed.logs==(current->narrowed<0),"exact negative-only log count");
    require(strcmp(observed.trace,current->narrowed<0?"VCDL":"VCD")==0,
            "complete independent callback trace");
    if (current->narrowed<0)
        snprintf(expected_log,sizeof(expected_log),
                "settid: WARNING: do_syscall returns %d\n",current->narrowed);
    require(strcmp(observed.log,expected_log)==0,"exact original log text");
    require(!mode || carrier!=NULL,"actual Rust body called");
    return observed;
}
int main(void)
{
    int tids[4]={19,23,-7,0};
    const int original_tids[4]={19,23,-7,0};
    for (case_index=0;case_index<sizeof(cases)/sizeof(cases[0]);++case_index) {
        struct observation c,rust;
        current=&cases[case_index];
        c=run(0,tids);
        rust=run(1,tids);
        require(memcmp(c.bytes,rust.bytes,sizeof(c.bytes))==0 &&
                strcmp(c.trace,rust.trace)==0 && strcmp(c.log,rust.log)==0 &&
                c.result==rust.result && c.translations==rust.translations &&
                c.cpus==rust.cpus && c.calls==rust.calls && c.logs==rust.logs,
                "actual C/Rust observation parity");
        require(memcmp(tids,original_tids,sizeof(tids))==0,"tids buffer unchanged");
    }
    puts("PASS: 12 complete actual-C/actual-Rust settid cases; bytes/order/return/log/carrier");
    return 0;
}
