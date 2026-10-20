/* Linux control-plane collector extension, SOURCE PROTOTYPE ONLY.
 * Include after save_file() in the exact native_diagnostic_guest_collector.c.
 * Existing supervise() stays unchanged, including all descendant-reap checks.
 * Do NOT call shared retirement/teardown unless pair_run returns safe=1.
 * CPU discovery/assignment needs its own reviewed adapter and execution profile.
 */
#ifndef PAIR_ROOT
#define PAIR_ROOT "."
#endif
#ifndef PAIR_LAUNCHER
#define PAIR_LAUNCHER "/bin/mcexec"
#endif
static int pair_worker(int i, int cpu)
{
    char cpuenv[32], core[16], work[PATH_MAX], app[32], name[PATH_MAX], status[256];
    struct result r;
    snprintf(cpuenv,sizeof cpuenv,"PAIR_CPU=%d",cpu);
    snprintf(core,sizeof core,"%d",cpu);
    snprintf(work,sizeof work,PAIR_ROOT "/two-app/work%d",i);
    snprintf(app,sizeof app,"/apps/app%d",i);
    char *av[]={PAIR_LAUNCHER,"-t","1","-c",core,"0",app,NULL};
    char *env[]={"PATH=/usr/bin:/bin","COKERNEL_PATH=/apps",cpuenv,NULL};
    /* A separate supervisor process owns each waitpid(-1) domain. */
    supervise(PAIR_LAUNCHER,av,env,work,10000,&r);
    int good=!r.fault && !r.timeout && r.clean && r.status==0 &&
        r.out.eof && r.err.eof && r.out.observed==r.out.kept &&
        r.err.observed==r.err.kept;
    snprintf(name,sizeof name,PAIR_ROOT "/evidence/app%d.stdout",i);
    if(save_file(name,r.out.data,r.out.kept))good=0;
    snprintf(name,sizeof name,PAIR_ROOT "/evidence/app%d.stderr",i);
    if(save_file(name,r.err.data,r.err.kept))good=0;
    int n=snprintf(status,sizeof status,
        "{\"app\":%d,\"cpu\":%d,\"raw_wait_status\":%d,\"clean\":%d,\"fault\":%d,\"timeout\":%d,\"started_ns\":%llu,\"finished_ns\":%llu}\n",
        i,cpu,r.status,r.clean,r.fault,r.timeout,
        (unsigned long long)r.started,(unsigned long long)r.finished);
    snprintf(name,sizeof name,PAIR_ROOT "/evidence/app%d.status.json",i);
    if(n<0 || (size_t)n>=sizeof status || save_file(name,status,(size_t)n))good=0;
    snprintf(name,sizeof name,"evidence/app%d.result",i);
    if(save_file(name,&r,sizeof r))good=0;
    /* clean=0 must propagate separately even when evidence writing failed. */
    return !r.clean ? 2 : !good;
}

static int pair_run_assigned(const int cpus[2], int *safe)
{
    int joined[2]={0,0}, statuses[2]={-1,-1}, bad=0;
    pid_t owners[2]={-1,-1};
    *safe=1; /* no children exist on capability refusal */
    if(cpus[0]<0 || cpus[1]<0 || cpus[0]>=1024 || cpus[1]>=1024 || cpus[0]==cpus[1])return 77;
    if(mkdir(PAIR_ROOT "/two-app",0700) || mkdir(PAIR_ROOT "/two-app/work0",0700) ||
       mkdir(PAIR_ROOT "/two-app/work1",0700))return 1;
    uint64_t started=now_ns();
    if(!started)return 1;
    uint64_t end=bounded_deadline(started+15000*MS,0);
    *safe=0;
    for(int i=0;i<2;i++) {
        owners[i]=fork();
        if(owners[i]==0) {
            /* Become subreaper inside each supervisor: orphan mcexec helpers
             * must remain in its own waitpid(-1) ownership domain. */
            if(prctl(PR_SET_CHILD_SUBREAPER,1))_exit(2);
            _exit(pair_worker(i,cpus[i]));
        }
        if(owners[i]<0){bad=1;joined[i]=1;break;}
    }
    for(int i=0;i<2;i++)if(owners[i]<0)joined[i]=1;
    while(!joined[0] || !joined[1]) {
        for(int i=0;i<2;i++)if(!joined[i]) {
            pid_t r=waitpid(owners[i],&statuses[i],WNOHANG);
            if(r==owners[i])joined[i]=1;
            else if(r<0 && errno!=EINTR)return 1; /* uncertain: safe stays0 */
        }
        if(joined[0] && joined[1])break;
        uint64_t now=now_ns();
        if(!now || now>=end)return 1; /* preserve owners; never shared teardown */
        struct timespec t={0,1000000};nanosleep(&t,NULL);
    }
    *safe=1;
    for(int i=0;i<2;i++)if(owners[i]>0) {
        if(!WIFEXITED(statuses[i]) || WEXITSTATUS(statuses[i])==2)*safe=0;
        if(statuses[i]!=0)bad=1;
    }
    return bad;
}

static int pair_run(int *safe)
{
    int cpus[2];
    *safe=1;
    if(pair_discover(cpus))return 77;
    return pair_run_assigned(cpus,safe);
}
