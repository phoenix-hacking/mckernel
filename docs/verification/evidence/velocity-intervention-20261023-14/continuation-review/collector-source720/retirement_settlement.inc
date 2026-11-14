/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Observe settlement before the strict gate mutates its PID/token ledgers.
 * Readiness never grants app, ownership, work or retirement acceptance. */
/* Error-only retained syscall facts. No acceptance or retry authority. */
static struct {
    int valid,n,errno_after,pid0,pid1;
    size_t bound;
    unsigned round;
} pair_settlement_snapshot_error;
static int pair_round_retirement_ready(const char *log)
{
    int seen[2]={0,0};unsigned attempts[2]={0,0},tokens_used=0;
    unsigned long long tokens[24];
    if(pair_results[0].pid<=0 || pair_results[1].pid<=0 ||
       pair_results[0].pid==pair_results[1].pid)return -1;
    for(const char *p=log;*p;) {
        const char *end=strchr(p,'\n');size_t n=end?(size_t)(end-p):strlen(p);
        if(n>=512) {
            const char *mark=strstr(p,"application retirement ");
            if(mark && (!end || mark<end))return -1;
            p=end?end+1:p+n;continue;
        }
        char line[512];memcpy(line,p,n);line[n]=0;p=end?end+1:p+n;
        char *mark=strstr(line,"application retirement ");if(!mark)continue;
        unsigned osid=0;unsigned long generation=0;int pid=0,error=0,used=0;
        unsigned long long token=0;
        if(sscanf(mark,"application retirement os=%u generation=%lu pid=%d token=%llu errno=%d%n",
                  &osid,&generation,&pid,&token,&error,&used)!=5 || mark[used])return -1;
        for(int i=0;i<2;i++)if(pid==pair_results[i].pid) {
            if(osid || generation!=1 || !token || seen[i] ||
               (error!=-11 && error!=0) || ++attempts[i]>12)return -1;
            for(unsigned j=0;j<tokens_used;j++)if(tokens[j]==token)return -1;
            if(tokens_used==24)return -1;
            tokens[tokens_used++]=token;seen[i]=error==0;
        }
    }
    return seen[0] && seen[1];
}
static int pair_round_retirement_snapshot(char *log,size_t capacity,uint64_t outer_deadline)
{
    const uint64_t window=5000*MS;
    uint64_t begin=now_ns();
    pair_fail_phase="kernel_retirement_wait";
    if(!begin || begin>UINT64_MAX-window || !outer_deadline || begin>=outer_deadline || capacity<2)return -1;
    uint64_t deadline=bounded_deadline(begin+window,0);
    if(deadline>outer_deadline)deadline=outer_deadline;
    uint64_t previous=begin;
    for(;;) {
        uint64_t before=now_ns();
        if(!before || before<previous || before>=deadline)return -1;
        int n=long_kernel_snapshot(log,capacity-1);
        int snapshot_errno=errno;
        if(n<=0 || (size_t)n>capacity-1) {
            pair_settlement_snapshot_error.valid=1;
            pair_settlement_snapshot_error.n=n;
            pair_settlement_snapshot_error.errno_after=snapshot_errno;
            pair_settlement_snapshot_error.bound=capacity-1;
            pair_settlement_snapshot_error.round=pair_active_round;
            pair_settlement_snapshot_error.pid0=pair_results[0].pid;
            pair_settlement_snapshot_error.pid1=pair_results[1].pid;
            return -1;
        }
        log[n]=0;
        int ready=pair_round_retirement_ready(log);
        uint64_t after=now_ns();
        if(ready<0 || !after || after<before || after>=deadline)return -1;
        if(ready)return n;
        previous=after;
        uint64_t remaining=deadline-after,delay=remaining<10*MS?remaining:10*MS;
        struct timespec pause={0,(long)delay};
        if(nanosleep(&pause,NULL) && errno!=EINTR)return -1;
    }
}
