/* Exactly ten rounds, one already-booted OS. No repeat/duration interface. */
static int pair_round_empty(void)
{
    uint64_t begin=now_ns(),end=bounded_deadline(begin+5000*MS,0);
    while(begin) {
        uint64_t current=now_ns();if(!current || current>=end)return 0;
        int state=retired_at("/proc/mcos0");if(state==1)return 1;if(state<0)return 0;
        struct timespec pause={0,10000000};nanosleep(&pause,NULL);
    }
    return 0;
}
static int pair_round_mark(int fd,const char *kind,unsigned round,uint64_t stamp,int empty)
{
    char b[256];int n=snprintf(b,sizeof b,"ND_PAIR_ROUND_%s {\"round\":%u,\"time_ns\":%llu,\"procfs_empty\":%s}\n",kind,round,(unsigned long long)stamp,empty?"true":"false");
    return n<0 || (size_t)n>=sizeof b || write_all(fd,b,(size_t)n)?-1:0;
}
static int pair_run_launch_expansion(int console,int *safe,int *empty)
{
    pair_seen_pid_count=0;pair_seen_token_count=0;pair_trace_total=0;*empty=0;
    for(unsigned i=0;i<10;i++)pair_trace_records[i].fd=-1;
    for(pair_active_round=0;pair_active_round<10;pair_active_round++) {
        *safe=1;
        if(!pair_round_empty())return -1;
        int n=snprintf(pair_evidence_dir,sizeof pair_evidence_dir,PAIR_ROOT "/evidence/round%u",pair_active_round);
        if(n<0 || (size_t)n>=sizeof pair_evidence_dir || mkdir(pair_evidence_dir,0700))return -1;
        uint64_t start=now_ns();if(!start || pair_round_mark(console,"START",pair_active_round,start,1))return -1;
        if(pair_run(safe) || !*safe || pair_load_results())return -1;
        if(!pair_round_empty() || pair_round_gate())return -1;
        uint64_t finish=now_ns();
        if(!finish || finish<start || pair_results[0].started<start || pair_results[1].started<start ||
           pair_results[0].finished>finish || pair_results[1].finished>finish)return -1;
        if(publish_pair(console,1) || pair_round_mark(console,"END",pair_active_round,finish,1))return -1;
        char name[PATH_MAX],row[160];n=snprintf(name,sizeof name,"%s/round.json",pair_evidence_dir);
        int size=snprintf(row,sizeof row,"{\"round\":%u,\"started_ns\":%llu,\"finished_ns\":%llu,\"procfs_empty\":true}\n",pair_active_round,(unsigned long long)start,(unsigned long long)finish);
        if(n<0 || (size_t)n>=sizeof name || size<0 || (size_t)size>=sizeof row || save_file(name,row,(size_t)size))return -1;
    }
    *empty=1;return 0;
}
