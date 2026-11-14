static int baseline_failure_export(int console,const char *last,size_t bytes)
{
    if(!pair_rounds_initialized || bytes==0 || bytes>=1048576)return -1;
    /* Main saved its fresh snapshot. Prefer the exact immutable gate input
     * when available; never transport both snapshots or grow the raw budget. */
    int gate=pair_gate_valid && pair_gate_round==pair_active_round;
    const char *path=PAIR_ROOT "/evidence/kernel.log",*kind="current_raw";
    if(gate) {
        if(!pair_gate_bytes || pair_gate_bytes>=1048576)return -1;
        path=PAIR_ROOT "/evidence/gate.raw";kind="gate_raw";
        last=pair_gate_log;bytes=pair_gate_bytes;
        if(save_file(path,last,bytes))return -1;
    }
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
    struct stat identity;int bad=fd<0 || fstat(fd,&identity);
    if(!bad)bad=pair_diagnostic_file(console,fd,&identity,last,bytes,kind,pair_active_round);
    if(fd>=0 && close(fd))bad=1;
    if(bad)return -1;
    if(gate) {
        char row[384];int n=snprintf(row,sizeof row,"ND_PAIR_GUARD_CONTEXT {\"round\":%u,\"phase\":\"%s\",\"pids\":[%d,%d],\"cpus\":[0,1],\"gate_bytes\":%zu,\"snapshot\":\"gate_raw\"}\n",pair_active_round,pair_fail_phase,pair_results[0].pid,pair_results[1].pid,bytes);
        if(n<0 || (size_t)n>=sizeof row || write_all(console,row,(size_t)n))return -1;
    }
    for(unsigned round=0;round<10;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];
        if(r->fd<0)break;
        if(!r->bytes || r->offset>pair_trace_total || r->bytes>pair_trace_total-r->offset ||
           pair_diagnostic_file(console,r->fd,&r->identity,pair_trace_authenticated+r->offset,r->bytes,"retained",round))return -1;
    }
    return 0;
}

static int baseline_finish(int console,int safe,int good)
{
#ifdef ND_PAIR_LAUNCH_EXPANSION
    static char kernel_log[1048576];
#else
    static char kernel_log[262144];
#endif
    int n = klogctl(3, kernel_log, sizeof kernel_log);
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
    else if (save_file(PAIR_ROOT "/evidence/kernel.log", kernel_log, (size_t)n) || console < 0) good = 0;
    else {
#ifdef ND_PAIR_LAUNCH_EXPANSION
        if(good) { if(pair_trace_publish(console,kernel_log,(size_t)n))good=0; }
        else if(safe && pair_rounds_initialized && baseline_failure_export(console,kernel_log,(size_t)n))good=0;
#else
        if(write_all(console,kernel_log,(size_t)n) || write_all(console,"\n",1))good=0;
#endif
    }
    return good;
}
static int corrected_finish(int console,int safe,int good)
{
#ifdef ND_PAIR_LAUNCH_EXPANSION
    static char kernel_log[1048576];
#else
    static char kernel_log[262144];
#endif
    int n = klogctl(3, kernel_log, sizeof kernel_log);
#ifdef ND_PAIR_LAUNCH_EXPANSION
    int main_log_saved = 0;
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
    else if (save_file(PAIR_ROOT "/evidence/kernel.log", kernel_log, (size_t)n)) good = 0;
    else main_log_saved = 1;
    if (console < 0) good = 0;
    if(good) { if(pair_trace_publish(console,kernel_log,(size_t)n))good=0; }
    else if(safe && console >= 0 && pair_rounds_initialized &&
            pair_failure_export(console,main_log_saved ? kernel_log : NULL,
                                main_log_saved ? (size_t)n : 0))good=0;
#else
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
    else if (save_file(PAIR_ROOT "/evidence/kernel.log", kernel_log, (size_t)n) || console < 0) good = 0;
    else {
        if(write_all(console,kernel_log,(size_t)n) || write_all(console,"\n",1))good=0;
    }
#endif
    return good;
}
