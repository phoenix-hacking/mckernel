/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual retained Linux launch/result/resource providers. Quotas and LONG
 * orchestration live in Rust. Injection below is translation-unit private and
 * used only by the host regression fixture; production selects these defaults. */
#include "pair_long_producer.h"
struct long_provider {
    int (*discover)(int [2]);
    int (*launch)(const int [2],int *);
    int (*load)(void);
    int (*empty)(void);
    int (*snapshot)(int,char *,int);
};
static struct long_provider long_provider={pair_discover,pair_run_assigned,pair_load_results,pair_round_empty,klogctl};
static int long_kernel_snapshot(char *data,size_t count)
{ return count>INT_MAX?-1:long_provider.snapshot(3,data,(int)count); }
struct long_context { int console,spool; uint64_t deadline,bytes;struct stat identity; char report[4096]; };
static uint64_t long_now(void *p){(void)p;return now_ns();}
static int32_t long_empty(void *p,uint32_t round,uint64_t deadline)
{
    struct long_context *ctx=p;(void)round;ctx->deadline=deadline;
    uint64_t before=now_ns();
    if(!before || before>=deadline)return 0;
    int state=long_provider.empty();uint64_t after=now_ns();
    return state==1 && after>=before && after<deadline;
}
static int32_t long_pair(void *p,uint32_t round,uint64_t deadline,struct pair_long_pair *out)
{
    struct long_context *ctx=p;int cpus[2],safe=1,code=-1;ctx->deadline=deadline;
    memset(out,0,sizeof *out);out->strict_gate_result=-1;
    if(round>=2048)return -1;
    pair_active_round=round;
    int n=snprintf(pair_evidence_dir,sizeof pair_evidence_dir,PAIR_ROOT "/evidence/round%u",round);
    if(n<0 || (size_t)n>=sizeof pair_evidence_dir || mkdir(pair_evidence_dir,0700))goto done;
    if(long_provider.discover(cpus))goto done;
    code=long_provider.launch(cpus,&safe);
    out->ownership_complete=safe;
    if(!safe || code || long_provider.load())return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        out->apps[i]=(struct pair_long_app){r->pid,r->started,r->reaped,r->finished,r->status,r->clean,r->out.eof,r->err.eof};
    }
    /* Joined owners alone cannot prove procfs/workspace release. */
    if(!long_empty(ctx,round,deadline)){out->ownership_complete=0;return -1;}
    if(pair_round_gate())return -1;
    int fd=open(PAIR_ROOT "/evidence/current-report",O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW|O_CLOEXEC,0600);
    if(fd<0)return -1;
    int bad=publish_pair(fd,1);off_t size=lseek(fd,0,SEEK_END);
    if(size<=0 || size>=(off_t)sizeof ctx->report || pread(fd,ctx->report,(size_t)size,0)!=size)bad=1;
    if(close(fd))bad=1;
    if(unlink(PAIR_ROOT "/evidence/current-report"))bad=1;
    if(bad)return -1;
    struct pair_trace_record *trace=&pair_trace_records[round];
    out->os=pair_os;out->generation=pair_generation;out->strict_gate_result=0;
    out->report=(struct pair_long_bytes){(const uint8_t *)ctx->report,(size_t)size};
    out->trace=(struct pair_long_bytes){(const uint8_t *)pair_trace_authenticated+trace->offset,trace->bytes};
    return 0;
done:
    out->ownership_complete=safe;return -1;
}
static ptrdiff_t long_retain(void *p,const uint8_t *data,size_t size)
{
    struct long_context *ctx=p;
    if(!size || size>268435456u-ctx->bytes ||
       ctx->bytes+size!=pair_trace_total || memcmp(data,pair_trace_authenticated+ctx->bytes,size))return -1;
    if(write_all(ctx->spool,data,size))return -1;
    ctx->bytes+=size;
    if(fstat(ctx->spool,&ctx->identity) || ctx->identity.st_size!=(off_t)ctx->bytes ||
       !S_ISREG(ctx->identity.st_mode) || ctx->identity.st_nlink!=1)return -1;
    return (ptrdiff_t)size;
}
static ptrdiff_t long_read(void *p,uint64_t offset,uint8_t *data,size_t size)
{
    struct long_context *ctx=p;struct stat before,after;
    if(offset>ctx->bytes || size>ctx->bytes-offset ||
       fstat(ctx->spool,&before) || !pair_trace_same(&before,&ctx->identity))return -1;
    ssize_t n=pread(ctx->spool,data,size,(off_t)offset);
    if(n!=(ssize_t)size || memcmp(data,pair_trace_authenticated+offset,size) ||
       fstat(ctx->spool,&after) || !pair_trace_same(&before,&after))return -1;
    return n;
}
static ptrdiff_t long_write(void *p,const uint8_t *data,size_t size)
{
    struct long_context *ctx=p;uint64_t before=now_ns();
    if(!before || before>=ctx->deadline || write_all(ctx->console,data,size))return -1;
    uint64_t after=now_ns();
    return after>=before && after<ctx->deadline?(ptrdiff_t)size:-1;
}
static const struct pair_long_operations long_operations={long_now,long_empty,long_pair,long_retain,long_read,long_write};
static int long_dispatch(int console,int *safe,int *empty)
{
    struct long_context ctx={.console=console,.spool=-1,.deadline=now_ns()+7200000000000ull};
    struct pair_long_summary summary={0};*safe=1;*empty=0;
    pair_seen_pid_count=0;pair_seen_token_count=0;pair_trace_total=0;pair_rounds_initialized=1;
    ctx.spool=open(PAIR_ROOT "/evidence/long-trace.spool",O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW|O_CLOEXEC,0600);
    if(ctx.spool<0)return -1;
    int code=pair_run_long_session(&ctx,&long_operations,&summary);
    *safe=summary.ownership_complete;*empty=code==0 && summary.completed==1 && *safe;
    if(close(ctx.spool))return -1;
    return code;
}
