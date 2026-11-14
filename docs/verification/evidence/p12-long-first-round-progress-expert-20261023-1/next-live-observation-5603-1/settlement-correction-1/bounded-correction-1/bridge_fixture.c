/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Full actual bridge with retained supervise/fork/exec/wait/EOF/result loading;
 * only resource/procfs/kernel trace providers are controlled Linux fixtures. */
#include <dirent.h>
static DIR *fixture_opendir(const char *);
#define opendir fixture_opendir
#define ND_PAIR_LAUNCH_EXPANSION
#define ND_PAIR_LONG
#define main preserved_collector_main
#include "pair_collector.c"
#undef main
#undef opendir
static int controlled_mode;
static DIR *fixture_opendir(const char *path) {
    if(!strcmp(path,"/proc/mcos0")) {
        if(controlled_mode==8){errno=EIO;return NULL;}
        return opendir("./proc-empty");
    }
    return opendir(path);
}
static int controlled_discover(int cpus[2]) {
    cpus[0]=0;cpus[1]=1;pair_os=0;pair_generation=1;pair_host_cpus[0]=1;pair_host_cpus[1]=2;return 0;
}
static int controlled_snapshot(int type,char *out,int size) {
    (void)type;int used=0,n;
    n=snprintf(out,size,"NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0\ncontrol accepted os=0 generation=1 port=501 guest_cpu=0 linux_cpu=1 cookie=1 receive=10000 send=20000 bytes=16384 reference=0 remote_cookie=30000\ncontrol accepted os=0 generation=1 port=501 guest_cpu=1 linux_cpu=2 cookie=2 receive=40000 send=50000 bytes=16384 reference=0 remote_cookie=60000\n");
    if(n<0 || n>=size)return -1;used=n;
    for(int i=0;i<2;i++) {
        int pid=pair_results[i].pid;
        n=snprintf(out+used,size-used,
          "application SCHEDULE os=0 generation=1 pid=%d cpu=%d\n"
          "application procfs published os=0 generation=1 pid=%d tid=%d\n"
          "application_syscall=delivered os=0 generation=1 pid=%d worker=%d delivery=1 cpu=%d number=1\n"
          "application_syscall=return_route os=0 generation=1 pid=%d worker=%d delivery=1 launcher_cpu=%d guest_cpu=%d\n"
          "application_syscall=returned os=0 generation=1 pid=%d worker=%d delivery=1 cpu=%d value=0\n"
          "application_syscall=delivered os=0 generation=1 pid=%d worker=%d delivery=2 cpu=%d number=231\n",
          pid,i,pid,pid,pid,100+i,i,pid,100+i,1-i,i,pid,100+i,i,pid,100+i,i);
        if(n<0 || n>=size-used)return -1;used+=n;
        if(controlled_mode!=1) {
            n=snprintf(out+used,size-used,"application_process=cleanup_requested os=0 generation=1 pid=%d intent_errno=%d\n",pid,controlled_mode==2?-1:0);
            if(n<0 || n>=size-used)return -1;used+=n;
        }
        if(controlled_mode!=3) {
            n=snprintf(out+used,size-used,"application cleanup ACK os=0 generation=%d pid=%d token=%d errno=0 abandoned=0\n",controlled_mode==4?2:1,pid,1000+i);
            if(n<0 || n>=size-used)return -1;used+=n;
            if(controlled_mode==5) {n=snprintf(out+used,size-used,"application cleanup ACK os=0 generation=1 pid=%d token=%d errno=0 abandoned=0\n",pid,1000+i);if(n<0 || n>=size-used)return -1;used+=n;}
        }
        n=snprintf(out+used,size-used,"application retirement os=0 generation=1 pid=%d token=%d errno=%d\napplication procfs deleted os=0 generation=1 pid=%d tid=%d\n",pid,controlled_mode==6?2000:2000+i,controlled_mode==7?-11:0,pid,pid);
        if(n<0 || n>=size-used)return -1;used+=n;
        if(controlled_mode==1) {
            n=snprintf(out+used,size-used,"application_process=release os=0 generation=1 pid=%d cleanup_errno=0\n",pid);
            if(n<0 || n>=size-used)return -1;used+=n;
        }
    }
    return used;
}
extern int old_trace_witness(const char *,int,int);
int bridge_fixture(int mode) {
    controlled_mode=mode;pair_seen_pid_count=0;pair_seen_token_count=0;pair_trace_total=0;
    if(mkdir("proc-empty",0700))return 89;
    long_provider.discover=controlled_discover;long_provider.snapshot=controlled_snapshot;
    if(long_provider.empty!=pair_round_empty)return 90;
    int phase_console=open("controlled-phase-wire",O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC,0600);
    if(phase_console<0)return 91;
    struct long_context ctx={.console=phase_console,.spool=-1,.deadline=now_ns()+10000000000ull};
    struct pair_long_pair pair;int code=long_operations.run_pair(&ctx,0,ctx.deadline,&pair);
    if(close(phase_console))return 92;
    if(mode==8)return code!=0 && pair.ownership_complete==0?0:81;
    if(mode==1) {
        char log[65536];if(controlled_snapshot(3,log,sizeof log)<=0)return 85;
        for(int i=0;i<2;i++)if(old_trace_witness(log,pair_results[i].pid,i))return 86;
    }
    if(mode)return code!=0?0:82;
    char log[65536];if(controlled_snapshot(3,log,sizeof log)<=0)return 87;
    for(int i=0;i<2;i++)if(old_trace_witness(log,pair_results[i].pid,i)==0)return 88;
    if(code || pair.strict_gate_result || !pair.ownership_complete || pair.report.len<100)return 83;
    if(save_file(PAIR_ROOT "/full-report",pair.report.ptr,pair.report.len) || save_file(PAIR_ROOT "/full-trace",pair.trace.ptr,pair.trace.len))return 84;
    return 0;
}

/* Last-quota postflight uses the actual production default callback, real
 * Linux workspace metadata/content reads and original procfs iterator. */
int final_workspace_fixture(int mode)
{
    char name[64];snprintf(name,sizeof name,"workspace-final-%d",mode);
    if(mkdir(name,0700) || chdir(name) || mkdir("proc-empty",0700))return -1;
    pair_active_round=0;
    if(pair_round_workdirs())return -1;
    if(mode==9) {
        int fd=open("two-app/work0/leftover",O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);
        if(fd<0 || close(fd))return -1;
    } else if(mode==10) {
        if(rename("two-app/work0","two-app/retained-old-work0") || mkdir("two-app/work0",0700))return -1;
    }
    if(long_provider.empty!=pair_round_empty)return -1;
    struct long_context context={0};
    return long_empty(&context,359,now_ns()+10000000000ull);
}
static int final_mode,final_restore_calls,final_terminal_calls;
static int final_save(const char *path,const void *bytes,size_t count)
{(void)bytes;(void)count;return (final_mode==3 && strstr(path,"kernel.log")) || (final_mode==7 && strstr(path,"teardown"))?-1:0;}
static int final_klog(int action,char *bytes,int count)
{
    (void)bytes;(void)count;
    if(action==3)return final_mode==4?-1:0;
    if(action==8 && ++final_restore_calls==2 && final_mode==5)return -1;
    return 0;
}
static int final_open(const char *path,int flags,...)
{(void)flags;return !strcmp(path,"/case/evidence") && final_mode!=6?42:-1;}
static int final_syncfs(int fd){return fd==42 && final_mode!=1?0:-1;}
static int final_close(int fd){return fd==42 && final_mode!=2?0:-1;}
static int final_write(int fd,const void *bytes,size_t count)
{(void)fd;(void)bytes;(void)count;return 0;}
#define save_file final_save
#define klogctl final_klog
#define open final_open
#define syncfs final_syncfs
#define close final_close
#define write_all final_write
#define remain_pid1() return -1
#define long_complete() (++final_terminal_calls,pair_complete_long_session(finish_ctx,finish_ops,finish_summary,not_before,absolute))
int final_gate_fixture(int mode,void *finish_ctx,const struct pair_long_operations *finish_ops,
    struct pair_long_summary *finish_summary,uint64_t not_before,uint64_t absolute)
{
    final_mode=mode;final_restore_calls=final_terminal_calls=0;
    struct result payload={0};int good=1,safe=1,empty=1,loaded=3,console=43,saved_level=7;
#include "actual-final-gates.inc"
    return final_terminal_calls==1?0:-1;
}
