#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#define PAIR_ROOT "case"
#define ND_PAIR_TWO_ROUNDS 1
#define STREAM_LIMIT 1024u
#define FRAME_LIMIT 4096u
#define MS 1000000ull
struct stream {
    unsigned char data[STREAM_LIMIT];
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
    struct stream out, err;
    int pid;
    int status, fault, timeout, clean;
    int child_stage, child_errno;
    uint64_t started, reaped, finished;
};
static unsigned pair_active_round;
static char pair_evidence_dir[PATH_MAX];
static unsigned long pair_generation=1;
static unsigned pair_os;
static int pair_host_cpus[2]={1,2};
static uint64_t fixture_clock=1000000000ull;
static int scenario,run_calls,app_launches;
static char fixture_log[65536];static size_t log_size;
static uint64_t now_ns(void){fixture_clock+=2000000000ull;return fixture_clock;}
static uint64_t bounded_deadline(uint64_t end,uint64_t reserve){(void)reserve;return end;}
static int retired_at(const char *path){(void)path;return scenario==4 && run_calls==1?0:1;}
#include "actual_shared_functions.inc"
#include "actual_result_io.inc"
static int fixture_klogctl(int action,char *buf,int length){(void)action;if(log_size>=(size_t)length)return -1;memcpy(buf,fixture_log,log_size);return (int)log_size;}
#define klogctl fixture_klogctl
#include "../candidate/pair_two_round_support.inc"
static void add(const char *fmt,...){va_list ap;va_start(ap,fmt);int n=vsnprintf(fixture_log+log_size,sizeof fixture_log-log_size,fmt,ap);va_end(ap);assert(n>=0 && (size_t)n<sizeof fixture_log-log_size);log_size+=(size_t)n;}
static int pair_run(int *safe)
{
    run_calls++;*safe=1;
    if(scenario==3){*safe=0;return 1;}
    if(scenario==7 && pair_active_round==1)assert(save_file("case/two-app/work0/stale","x",1)==0);
    if(pair_round_workdirs())return 1;
    for(int i=0;i<2;i++) {
        struct result r;memset(&r,0,sizeof r);r.pid=1001+(int)pair_active_round*2+i;
        if(scenario==5 && pair_active_round==1 && i==0)r.pid=1001;
        r.clean=1;r.started=fixture_clock+10+(uint64_t)i*10;r.reaped=fixture_clock+200+(uint64_t)i*20;r.finished=fixture_clock+250+(uint64_t)i*10;
        const unsigned char *p=i?pair_round_stdout_1:pair_round_stdout_0;size_t size=i?sizeof pair_round_stdout_1:sizeof pair_round_stdout_0;
        memcpy(r.out.data,p,size);r.out.kept=size;r.out.observed=size;r.out.eof=r.err.eof=1;r.out.eof_ns=r.err.eof_ns=r.reaped-10;
        if((scenario==1 && pair_active_round==0 && i==0) || (scenario==8 && pair_active_round==1 && i==0))r.out.data[0]^=1;
        char name[PATH_MAX];int n=snprintf(name,sizeof name,"%s/app%d.result",pair_evidence_dir,i);assert(n>0 && (size_t)n<sizeof name);assert(save_file(name,&r,sizeof r)==0);app_launches++;
        int cpu=(scenario==2 && pair_active_round==0 && i==0)?1:i;
        unsigned long long token=(unsigned long long)r.pid*10+1;
        if(scenario==6 && pair_active_round==1 && i==0)token=10011;
        if(scenario==9 && pair_active_round==0 && i==1)token=10011;
        add("application SCHEDULE os=0 generation=1 pid=%d cpu=%d\n",r.pid,cpu);
        add("application procfs published os=0 generation=1 pid=%d tid=%d\n",r.pid,r.pid);
        add("application_syscall=delivered os=0 generation=1 pid=%d worker=%d delivery=1 cpu=%d number=157\n",r.pid,r.pid+5000,cpu);
        add("application_syscall=return_route os=0 generation=1 pid=%d worker=%d delivery=1 launcher_cpu=%d guest_cpu=%d\n",r.pid,r.pid+5000,1-i,cpu);
        add("application_syscall=returned os=0 generation=1 pid=%d worker=%d delivery=1 cpu=%d value=0\n",r.pid,r.pid+5000,cpu);
        add("application_syscall=delivered os=0 generation=1 pid=%d worker=%d delivery=2 cpu=%d number=231\n",r.pid,r.pid+5000,cpu);
        add("application retirement os=0 generation=1 pid=%d token=%llu errno=-11\n",r.pid,token);
        add("application retirement os=0 generation=1 pid=%d token=%llu errno=0\n",r.pid,token+1);
        add("application_process=release os=0 generation=1 pid=%d cleanup_errno=0\n",r.pid);
        add("application procfs deleted os=0 generation=1 pid=%d tid=%d\n",r.pid,r.pid);
    }
    fixture_clock+=1000;return 0;
}
#include "../candidate/pair_two_round_run.inc"
int main(int argc,char **argv)
{
    assert(argc==3 && chdir(argv[2])==0);scenario=atoi(argv[1]);assert(scenario>=0 && scenario<=9);
    assert(mkdir("case",0700)==0 && mkdir("case/evidence",0700)==0);
    add("NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0\n");
    add("control accepted os=0 generation=1 port=501 guest_cpu=0 linux_cpu=1 cookie=1 receive=10000000 send=20000000 bytes=16384 reference=1 remote_cookie=30000000\n");
    add("control accepted os=0 generation=1 port=501 guest_cpu=1 linux_cpu=2 cookie=2 receive=40000000 send=50000000 bytes=16384 reference=1 remote_cookie=60000000\n");
    int safe=1,empty=0;int result=pair_run_two_rounds(1,&safe,&empty);
    if(result==0){assert(write_all(1,fixture_log,log_size)==0);const char done[]="ND_PAIR_ROUNDS_COMPLETE {\"rounds\":2,\"os\":0,\"generation\":1,\"procfs_empty\":true}\n";assert(write_all(1,done,sizeof done-1)==0);}
    printf("FIXTURE_RESULT {\"scenario\":%d,\"result\":%d,\"safe\":%d,\"empty\":%d,\"runs\":%d,\"launches\":%d}\n",scenario,result,safe,empty,run_calls,app_launches);
    return 0;
}
