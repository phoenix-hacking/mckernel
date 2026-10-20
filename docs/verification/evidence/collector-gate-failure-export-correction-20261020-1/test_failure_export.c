#define ND_PAIR_LAUNCH_EXPANSION 1
#define PAIR_ROOT "."
#define klogctl fixture_klogctl
#define main fixture_unused_collector_main
#include "candidate/pair_collector.c"
#undef main
#undef klogctl
#include <assert.h>
#include <stdlib.h>
static int main_capture_mode;
int fixture_klogctl(int operation,char *out,int limit)
{
    (void)out;(void)limit;assert(operation==3);
    if(main_capture_mode==0){errno=EIO;return -1;}
    assert(main_capture_mode==1);return 0;
}
/* Exact consumed baseline/current finish blocks, with only the absolute /case
 * fixture-root adapter, and exact baseline exporter under a distinct name. */
#include "actual_finish_bodies.inc"
static char retained_raw[1048576];
static size_t retained_bytes;
static void setup(const char *root,const char *name,int gate)
{
    assert(chdir(root)==0 && mkdir(name,0700)==0 && chdir(name)==0);
    assert(mkdir("evidence",0700)==0);
    pair_active_round=0;pair_rounds_initialized=1;pair_gate_round=0;
    pair_gate_valid=gate;pair_gate_bytes=retained_bytes;
    memcpy(pair_gate_log,retained_raw,retained_bytes);
    memset(pair_results,0,sizeof pair_results); /* Actual failed64 PID mapping is unknown. */
    pair_trace_total=0;for(unsigned i=0;i<10;i++)pair_trace_records[i].fd=-1;
}
static char *capture(int fd,size_t *length)
{
    off_t n=lseek(fd,0,SEEK_END);assert(n>=0 && n<4*1048576);
    char *s=calloc((size_t)n+1,1);assert(s && lseek(fd,0,SEEK_SET)==0);
    size_t off=0;while(off<(size_t)n){ssize_t got=read(fd,s+off,(size_t)n-off);assert(got>0);off+=(size_t)got;}
    *length=off;return s;
}
static unsigned nybble(char c)
{assert((c>='0' && c<='9') || (c>='a' && c<='f'));return c<='9'?(unsigned)(c-'0'):(unsigned)(c-'a'+10);}
static void exact_raw(const char *s)
{
    size_t off=0;const char *p=s;
    while((p=strstr(p,"ND_PAIR_DIAGNOSTIC_CHUNK "))){
        size_t found=0;int used=0;
        assert(sscanf(p,"ND_PAIR_DIAGNOSTIC_CHUNK {\"kind\":\"gate_raw\",\"round\":0,\"offset\":%zu,\"hex\":\"%n",&found,&used)==1 && used>0 && found==off);
        p+=used;while(*p!='"'){
            assert(off<retained_bytes && p[1]);unsigned value=nybble(p[0])*16+nybble(p[1]);
            assert(value==(unsigned char)retained_raw[off++]);p+=2;
        }
    }
    assert(off==retained_bytes && strstr(s,"ND_PAIR_DIAGNOSTIC_END {\"kind\":\"gate_raw\""));
    assert(strstr(s,"ND_PAIR_GUARD_CONTEXT {\"round\":0,\"phase\":\"app0_trace_oracle\",\"pids\":[0,0],\"cpus\":[0,1]"));
}
static void run(const char *root,const char *name,int gate,int mode,int safe,int baseline,int expected)
{
    setup(root,name,gate);main_capture_mode=mode;
    int fd=open("diagnostic.stdout",O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC,0600);assert(fd>=0);
    assert(pair_round_fail(fd,"app0_trace_oracle",safe)==-1);
    assert((baseline?baseline_finish(fd,safe,0):corrected_finish(fd,safe,0))==0);
    size_t bytes=0;char *out=capture(fd,&bytes);assert(bytes>0);
    assert(strstr(out,"ND_PAIR_ROUND_FAIL {\"round\":0,\"phase\":\"app0_trace_oracle\""));
    assert(!strstr(out,"ND_PAIR_ROUNDS_COMPLETE") && !strstr(out,"ND_PAIR_ROUND_END"));
    if(expected){exact_raw(out);assert(access("evidence/gate.raw",F_OK)==0);}
    else {assert(!strstr(out,"ND_PAIR_DIAGNOSTIC_BEGIN") && !strstr(out,"ND_PAIR_GUARD_CONTEXT"));assert(access("evidence/gate.raw",F_OK)!=0);}
    if(mode==0)assert(access("evidence/kernel.log",F_OK)!=0);
    else {struct stat st;assert(stat("evidence/kernel.log",&st)==0 && st.st_size==0);}
    free(out);assert(close(fd)==0);
}
int main(int argc,char **argv)
{
    assert(argc==3);char root[PATH_MAX];assert(realpath(argv[1],root));
    int raw=open(argv[2],O_RDONLY|O_CLOEXEC|O_NOFOLLOW);assert(raw>=0);
    ssize_t n=read(raw,retained_raw,sizeof retained_raw);assert(n==79295 && close(raw)==0);retained_bytes=(size_t)n;
    run(root,"baseline_missing",1,0,1,1,0);run(root,"corrected_missing",1,0,1,0,1);
    puts("missing_main PASS baseline_suppressed_corrected_exact_retained_raw_and_failure_context");
    run(root,"baseline_empty",1,1,1,1,0);run(root,"corrected_empty",1,1,1,0,1);
    puts("empty_main PASS baseline_suppressed_corrected_exact_retained_raw_and_failure_context");
    run(root,"missing_without_gate",0,0,1,0,0);puts("missing_without_gate PASS no_fabricated_raw");
    run(root,"empty_without_gate",0,1,1,0,0);puts("empty_without_gate PASS no_fabricated_raw");
    run(root,"unsafe_missing",1,0,0,0,0);puts("unsafe_handoff PASS no_raw_publication");
    return 0;
}
