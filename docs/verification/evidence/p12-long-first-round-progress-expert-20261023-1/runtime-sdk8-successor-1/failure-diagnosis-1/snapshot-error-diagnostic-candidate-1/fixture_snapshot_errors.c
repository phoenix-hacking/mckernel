/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original/candidate snapshot and failure-export bodies; controlled snapshot/time/save providers.
 * Output uses a real private regular file. No root, guest, container, signal, workload or native qualification. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#define MS 1000000ull
static unsigned pair_active_round=21;
static struct { int pid; } pair_results[2]={{423},{424}};
static const char *pair_fail_phase="unset";
static uint64_t clock_ns;
static uint64_t now_ns(void){return clock_ns+=MS;}
static uint64_t bounded_deadline(uint64_t v,int unused){(void)unused;return v;}
static int writes_fail;
static int write_all(int fd,const void *p,size_t n)
{
    if(writes_fail){errno=EBADF;return -1;}
    return write(fd,p,n)==(ssize_t)n?0:-1;
}
static int snapshot_mode,snapshot_calls;
static const char ready_rows[]="application retirement os=0 generation=1 pid=423 token=1 errno=0\napplication retirement os=0 generation=1 pid=424 token=2 errno=0\n";
static int controlled_snapshot(int action,char *buf,int size)
{
    assert(action==3 && size==1048576);snapshot_calls++;
    if(snapshot_mode==0){errno=EACCES;return -1;}
    if(snapshot_mode==1){errno=ENOSYS;return 0;}
    if(snapshot_mode==2){errno=EEXIST;return size;}
    assert(snapshot_mode==3);assert((size_t)size>strlen(ready_rows));memcpy(buf,ready_rows,strlen(ready_rows));errno=EALREADY;return (int)strlen(ready_rows);
}
static struct {int (*snapshot)(int,char *,int);} long_provider={controlled_snapshot};
#if CANDIDATE
#include "candidate.long_kernel_snapshot.ACTUAL-BODY.inc"
#include "retirement_settlement.inc"
#else
#include "original.long_kernel_snapshot.ACTUAL-BODY.inc"
#include "retirement_settlement.inc.PREIMAGE"
#endif
struct long_context {int console,spool;uint64_t deadline,bytes;struct stat identity;char report[4096];};
static unsigned long_observed_round=21;
static const char *long_observed_phase="callback-gate";
static int long_observed_result=-5;
static struct {uint64_t rounds,launches,trace_bytes;} long_observed_summary={21,42,4473600};
static int long_phase(struct long_context *ctx,unsigned round,const char *phase)
{
    char line[192];int n=snprintf(line,sizeof line,"P12_LONG_PHASE round=%u stage=%s\n",round,phase);
    return n<=0 || (size_t)n>=sizeof line || write_all(ctx->console,line,(size_t)n)?-1:0;
}
static int save_file(const char *path,const void *p,size_t n){(void)path;(void)p;(void)n;return 0;}
#define PAIR_ROOT "/TESTONLY-unused-no-save-provider"
#if CANDIDATE
#include "candidate.long_snapshot_error_line.ACTUAL-BODY.inc"
#include "candidate.long_failure_export.ACTUAL-BODY.inc"
#else
#include "original.long_failure_export.ACTUAL-BODY.inc"
#endif
static unsigned count_marker(const char *text,const char *mark)
{
    unsigned n=0;for(const char *p=text;(p=strstr(p,mark));p+=strlen(mark))n++;return n;
}
int main(int argc,char **argv)
{
    assert(argc==2 && getuid()==geteuid() && getuid()==1000);
    snapshot_mode=atoi(argv[1]);assert(snapshot_mode>=0 && snapshot_mode<=3);
    FILE *capture=tmpfile();assert(capture);int fd=fileno(capture);assert(fd>=0);
    char log[1048577];int result=pair_round_retirement_snapshot(log,sizeof log,10000*MS);
    assert(snapshot_calls==1);
    if(snapshot_mode==3){assert(result==(int)strlen(ready_rows));assert(!strcmp(log,ready_rows));
#if CANDIDATE
        assert(!pair_settlement_snapshot_error.valid);
#endif
        assert(ftell(capture)==0);assert(!fclose(capture));puts("PASS_VALID_READY_NO_DIAGNOSTIC_OUTPUT");return 0;
    }
    assert(result==-1);int expected_n=snapshot_mode==0?-1:snapshot_mode==1?0:1048576;
    int expected_error=snapshot_mode==0?EACCES:snapshot_mode==1?ENOSYS:EEXIST;
#if CANDIDATE
    assert(pair_settlement_snapshot_error.valid && pair_settlement_snapshot_error.n==expected_n && pair_settlement_snapshot_error.errno_after==expected_error && pair_settlement_snapshot_error.bound==1048576 && pair_settlement_snapshot_error.round==21 && pair_settlement_snapshot_error.pid0==423 && pair_settlement_snapshot_error.pid1==424);
#endif
    assert(long_failure_export(fd,1)==-1 && snapshot_calls==2);
    assert(!fflush(capture) && !fseek(capture,0,SEEK_SET));char text[4096];size_t n=fread(text,1,sizeof text-1,capture);assert(!ferror(capture));text[n]=0;assert(!fclose(capture));
    assert(strstr(text,"ND_PAIR_LONG_ABORT\n") && strstr(text,"P12_LONG_FAILURE_TRACE_ERROR stage=snapshot\n") && !strstr(text,"TRACE_BEGIN"));
#if CANDIDATE
    assert(count_marker(text,"P12_LONG_SNAPSHOT_ERROR ")==2);char wanted[256];
    snprintf(wanted,sizeof wanted,"site=settlement n=%d errno_after=%d errno_valid=%d bound=1048576 round=21 pid0=423 pid1=424\n",expected_n,expected_error,expected_n<0);assert(strstr(text,wanted));
    snprintf(wanted,sizeof wanted,"site=failure_export n=%d errno_after=%d errno_valid=%d bound=1048576 round=21 pid0=423 pid1=424\n",expected_n,expected_error,expected_n<0);assert(strstr(text,wanted));
    assert(strstr(text,"ND_PAIR_LONG_ABORT\n")<strstr(text,"P12_LONG_SNAPSHOT_ERROR "));
    errno=ERANGE;writes_fail=1;long_snapshot_error_line(-1,"settlement",expected_n,expected_error,1048576,21,423,424);assert(errno==ERANGE);
#else
    assert(!count_marker(text,"P12_LONG_SNAPSHOT_ERROR "));
#endif
    /* Expose exact actual-body output for independent old/new comparison; no normaloracle record generated. */
    printf("PASS_SNAPSHOT_FAILURE mode=%d n=%d errno_after=%d snapshot_calls=%d\n",snapshot_mode,expected_n,expected_error,snapshot_calls);fputs(text,stdout);return 0;
}
