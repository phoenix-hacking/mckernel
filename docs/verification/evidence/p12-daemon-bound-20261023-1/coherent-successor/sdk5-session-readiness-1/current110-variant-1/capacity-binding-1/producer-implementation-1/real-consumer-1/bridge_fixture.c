/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Full actual bridge with retained supervise/fork/exec/wait/EOF/result loading;
 * only resource/procfs/kernel trace providers are controlled Linux fixtures. */
#define ND_PAIR_LAUNCH_EXPANSION
#define ND_PAIR_LONG
#define main preserved_collector_main
#include "pair_collector.c"
#undef main
static int controlled_mode;
static int controlled_discover(int cpus[2]) {
    cpus[0]=0;cpus[1]=1;pair_os=0;pair_generation=1;pair_host_cpus[0]=1;pair_host_cpus[1]=2;return 0;
}
static int controlled_empty(void){return controlled_mode==8?0:1;}
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
          "application_syscall=returned os=0 generation=1 pid=%d worker=%d delivery=1 cpu=%d value=0\n"
          "application_syscall=delivered os=0 generation=1 pid=%d worker=%d delivery=2 cpu=%d number=231\n",
          pid,i,pid,pid,pid,100+i,i,pid,100+i,i,pid,100+i,i);
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
    long_provider.discover=controlled_discover;long_provider.empty=controlled_empty;long_provider.snapshot=controlled_snapshot;
    struct long_context ctx={.console=-1,.spool=-1,.deadline=now_ns()+10000000000ull};
    struct pair_long_pair pair;int code=long_operations.run_pair(&ctx,0,ctx.deadline,&pair);
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
