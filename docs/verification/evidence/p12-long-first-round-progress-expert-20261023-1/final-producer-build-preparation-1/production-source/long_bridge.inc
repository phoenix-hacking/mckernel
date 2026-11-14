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
/* Linux control-plane diagnostics only. These records never authorize work,
 * ACK, release or completion. Emit before any callback that may not return. */
static uint32_t long_observed_round;
static const char *long_observed_phase="setup";
static int long_observed_result=-1;
static struct pair_long_summary long_observed_summary;
static int long_phase(struct long_context *ctx,uint32_t round,const char *phase)
{
    char line[192];
    long_observed_round=round;long_observed_phase=phase;
    int n=snprintf(line,sizeof line,"P12_LONG_PHASE round=%u stage=%s\n",round,phase);
    return n<=0 || (size_t)n>=sizeof line || write_all(ctx->console,line,(size_t)n)?-1:0;
}
static int long_failure_export(int console,int ownership_complete)
{
    struct long_context ctx={.console=console};
    char line[512];static char log[1048577];
    const char *failed_phase=long_observed_phase;
    int n=snprintf(line,sizeof line,
        "P12_LONG_FAILURE round=%u stage=%s pair_stage=%s result=%d ownership_complete=%d rounds=%llu launches=%llu trace_bytes=%llu\n",
        long_observed_round,failed_phase,pair_fail_phase,long_observed_result,
        ownership_complete,(unsigned long long)long_observed_summary.rounds,(unsigned long long)long_observed_summary.launches,
        (unsigned long long)long_observed_summary.trace_bytes);
    if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n))return -1;
    /* Reject success first, before an evidence callback can itself stall. */
    static const char abort_line[]="ND_PAIR_LONG_ABORT\n";
    if(write_all(console,abort_line,sizeof abort_line-1) ||
       long_phase(&ctx,long_observed_round,"failure-trace-snapshot"))return -1;
    n=long_kernel_snapshot(log,sizeof log-1);
    if(n<=0 || n==(int)sizeof log-1) {
        static const char error[]="P12_LONG_FAILURE_TRACE_ERROR stage=snapshot\n";
        (void)write_all(console,error,sizeof error-1);return -1;
    }
    if(long_phase(&ctx,long_observed_round,"failure-trace-save"))return -1;
    int saved=save_file(PAIR_ROOT "/evidence/long-failure.kernel.log",log,(size_t)n);
    if(saved) {
        static const char error[]="P12_LONG_FAILURE_TRACE_ERROR stage=save\n";
        if(write_all(console,error,sizeof error-1))return -1;
    }
    int count=snprintf(line,sizeof line,"P12_LONG_FAILURE_TRACE_BEGIN bytes=%d saved=%d\n",n,!saved);
    if(count<=0 || (size_t)count>=sizeof line || write_all(console,line,(size_t)count) ||
       write_all(console,log,(size_t)n) || (log[n-1]!='\n' && write_all(console,"\n",1)))return -1;
    count=snprintf(line,sizeof line,"P12_LONG_FAILURE_TRACE_END bytes=%d\n",n);
    return count<=0 || (size_t)count>=sizeof line || write_all(console,line,(size_t)count)?-1:0;
}

static int32_t long_empty(void *p,uint32_t round,uint64_t deadline)
{
    struct long_context *ctx=p;(void)round;ctx->deadline=deadline;
    uint64_t before=now_ns();
    if(!before || before>=deadline)return 0;
    int state=long_provider.empty();
    if(state!=1 || (pair_workspace_initialized && pair_round_workspace_verify(deadline)))return 0;
    uint64_t after=now_ns();
    return after>=before && after<deadline;
}
static int32_t long_pair(void *p,uint32_t round,uint64_t deadline,struct pair_long_pair *out)
{
    struct long_context *ctx=p;int cpus[2],safe=1,code=-1;ctx->deadline=deadline;
    memset(out,0,sizeof *out);out->strict_gate_result=-1;
    if(round>=2048)return -1;
    pair_active_round=round;
    if(long_phase(ctx,round,"round-evidence"))goto done;
    int n=snprintf(pair_evidence_dir,sizeof pair_evidence_dir,PAIR_ROOT "/evidence/round%u",round);
    if(n<0 || (size_t)n>=sizeof pair_evidence_dir || mkdir(pair_evidence_dir,0700))goto done;
    if(long_phase(ctx,round,"callback-discover") || long_provider.discover(cpus))goto done;
    if(long_phase(ctx,round,"callback-launch"))goto done;
    code=long_provider.launch(cpus,&safe);
    out->ownership_complete=safe;
    if(!safe || code)return -1;
    if(long_phase(ctx,round,"callback-load") || long_provider.load())return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        out->apps[i]=(struct pair_long_app){r->pid,r->started,r->reaped,r->finished,r->status,r->clean,r->out.eof,r->err.eof};
    }
    /* Joined owners alone cannot prove procfs/workspace release. */
    if(long_phase(ctx,round,"callback-postflight") || !long_empty(ctx,round,deadline)){out->ownership_complete=0;return -1;}
    if(long_phase(ctx,round,"callback-gate") || pair_round_gate())return -1;
    if(long_phase(ctx,round,"callback-report"))return -1;
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
static struct long_context long_final_context;
static struct pair_long_summary long_final_summary;
static uint64_t long_final_not_before;
static int long_final_pending;
static int long_complete(void)
{
    if(!long_final_pending)return -1;
    long_final_pending=0; /* No same-run terminal retry is permitted. */
    return pair_complete_long_session(&long_final_context,&long_operations,
        &long_final_summary,long_final_not_before,long_final_context.deadline);
}
static int long_dispatch(int console,int *safe,int *empty)
{
    (void)pair_run; /* unchanged short consumer retained, excluded from LONG dispatch */
    struct long_context ctx={.console=console,.spool=-1,.deadline=now_ns()+7200000000000ull};
    struct pair_long_summary summary={0};*safe=1;*empty=0;long_final_pending=0;
    pair_seen_pid_count=0;pair_seen_token_count=0;pair_trace_total=0;pair_rounds_initialized=1;
    memset(&long_observed_summary,0,sizeof long_observed_summary);long_observed_result=-1;
    if(long_phase(&ctx,0,"setup-spool"))return -1;
    ctx.spool=open(PAIR_ROOT "/evidence/long-trace.spool",O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW|O_CLOEXEC,0600);
    if(ctx.spool<0)return -1;
    int code=pair_run_long_session(&ctx,&long_operations,&summary);
    long_observed_result=code;long_observed_summary=summary;
    *safe=summary.ownership_complete;*empty=code==0 && *safe;
    if(close(ctx.spool)){long_observed_phase="spool-close";long_observed_result=-1;return -1;}
    if(code==0) {
        long_final_not_before=now_ns();
        if(!long_final_not_before || long_final_not_before>=ctx.deadline)return -1;
        long_final_context=ctx;long_final_summary=summary;long_final_pending=1;
    }
    return code;
}
