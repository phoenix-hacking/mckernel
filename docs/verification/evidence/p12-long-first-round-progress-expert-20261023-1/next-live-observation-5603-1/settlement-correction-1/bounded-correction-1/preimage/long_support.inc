/* Fixed ten-round Linux collector support. No kernel/worker ownership policy. */
#include "pair_round_oracles.h"
static struct stat pair_workspace[3];
static int pair_workspace_initialized;
static int pair_seen_pids[4096], pair_seen_pid_count;
static unsigned long long pair_seen_tokens[49152];
static unsigned pair_seen_token_count;
static int pair_round_workdirs(void)
{
    static const char *paths[]={PAIR_ROOT "/two-app",PAIR_ROOT "/two-app/work0",PAIR_ROOT "/two-app/work1"};
    if(pair_active_round==0)for(int i=0;i<3;i++)if(mkdir(paths[i],0700))return -1;
    for(int i=0;i<3;i++) {
        struct stat s;
        if(lstat(paths[i],&s) || !S_ISDIR(s.st_mode) || s.st_uid!=geteuid() ||
           s.st_gid!=getegid() || (s.st_mode&07777)!=0700)return -1;
        if(pair_active_round==0)pair_workspace[i]=s;
        else if(s.st_dev!=pair_workspace[i].st_dev || s.st_ino!=pair_workspace[i].st_ino ||
                s.st_uid!=pair_workspace[i].st_uid || s.st_gid!=pair_workspace[i].st_gid ||
                s.st_mode!=pair_workspace[i].st_mode || s.st_nlink!=pair_workspace[i].st_nlink)return -1;
        if(i) {
            DIR *d=opendir(paths[i]);if(!d)return -1;
            struct dirent *e;int bad=0;errno=0;
            while((e=readdir(d)))if(strcmp(e->d_name,".") && strcmp(e->d_name,".."))bad=1;
            if(errno)bad=1;
            if(closedir(d))bad=1;
            if(bad)return -1;
        }
    }
    pair_workspace_initialized=1;
    return 0;
}
/* Read-only postflight. No round0 mkdir or baseline replacement occurs here. */
static int pair_workspace_same(const struct stat *a,const struct stat *b)
{
    return S_ISDIR(a->st_mode) && a->st_dev==b->st_dev && a->st_ino==b->st_ino &&
        a->st_uid==b->st_uid && a->st_gid==b->st_gid && a->st_mode==b->st_mode &&
        a->st_nlink==b->st_nlink;
}
static int pair_round_workspace_verify(uint64_t deadline)
{
    static const char *paths[]={PAIR_ROOT "/two-app",PAIR_ROOT "/two-app/work0",PAIR_ROOT "/two-app/work1"};
    if(!pair_workspace_initialized)return -1;
    for(int i=0;i<3;i++) {
        uint64_t before=now_ns();struct stat first,opened,last;
        if(!before || before>=deadline || lstat(paths[i],&first) ||
            !pair_workspace_same(&first,&pair_workspace[i]))return -1;
        DIR *d=opendir(paths[i]);if(!d)return -1;
        int bad=fstat(dirfd(d),&opened) || !pair_workspace_same(&opened,&first);
        struct dirent *e;unsigned entries=0;errno=0;
        while(!bad && (e=readdir(d))) {
            if(++entries>(i?2u:4u)) {bad=1;break;}
            if(!strcmp(e->d_name,".") || !strcmp(e->d_name,".."))continue;
            if(i || (strcmp(e->d_name,"work0") && strcmp(e->d_name,"work1")))bad=1;
        }
        if(errno)bad=1;
        if(closedir(d))bad=1;
        uint64_t after=now_ns();
        if(bad || !after || after<before || after>=deadline || lstat(paths[i],&last) ||
            !pair_workspace_same(&last,&first))return -1;
    }
    return 0;
}
static int pair_round_streams(void)
{
    const unsigned char *expected[]={pair_round_stdout_0,pair_round_stdout_1};
    const size_t lengths[]={sizeof pair_round_stdout_0,sizeof pair_round_stdout_1};
    if(pair_os!=0 || pair_generation!=1 || pair_host_cpus[0]!=1 || pair_host_cpus[1]!=2)return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        if(r->pid<=0 || r->status || r->fault || r->timeout || !r->clean ||
           !r->out.eof || !r->err.eof || r->out.kept!=lengths[i] ||
           r->out.observed!=lengths[i] || r->err.kept || r->err.observed ||
           memcmp(r->out.data,expected[i],lengths[i]) || !r->started ||
           r->started>r->reaped || r->reaped>r->finished ||
           r->out.eof_ns<r->started || r->out.eof_ns>r->finished ||
           r->err.eof_ns<r->started || r->err.eof_ns>r->finished)return -1;
        for(int j=0;j<pair_seen_pid_count;j++)if(pair_seen_pids[j]==r->pid)return -1;
        if(pair_seen_pid_count>=4096)return -1;
        pair_seen_pids[pair_seen_pid_count++]=r->pid;
    }
    return pair_results[0].started<pair_results[1].reaped &&
           pair_results[1].started<pair_results[0].reaped?0:-1;
}
struct pair_round_delivery { unsigned long long worker,serial;unsigned number;int returned,routed,launcher; };
static int pair_round_trace(const char *log,int pid,int cpu)
{
    struct pair_round_delivery calls[256];unsigned count=0,exits=0,attempts=0;
    int schedules=0,published=0,deleted=0,releases=0,acks=0,last_errno=-1,terminal=0;
    for(const char *p=log;*p;) {
        const char *end=strchr(p,'\n');size_t n=end?(size_t)(end-p):strlen(p);
        if(n>=512) {const char *app=strstr(p,"application");if(app && (!end || app<end))return -1;p=end?end+1:p+n;continue;}
        char line[512];memcpy(line,p,n);line[n]=0;
        p=end?end+1:p+n;
        char *mark;unsigned osid=0;unsigned long generation=0;int found=0,c=-1,used=0;
        if((mark=strstr(line,"application_syscall="))) {
            char kind[24];int offset=0;
            if(sscanf(mark,"application_syscall=%23s os=%u generation=%lu pid=%d %n",kind,&osid,&generation,&found,&offset)!=4)return -1;
            if(found!=pid)continue;
            if(osid || generation!=1)return -1;
            unsigned long long worker=0,serial=0;unsigned number=0;long value=0;int launcher=-1;
            char *tail=mark+offset;struct pair_round_delivery *d=NULL;
            if(!strcmp(kind,"delivered")) {
                if(sscanf(tail,"worker=%llu delivery=%llu cpu=%d number=%u%n",&worker,&serial,&c,&number,&used)!=4 || tail[used] || !worker || !serial || c!=cpu || terminal || number==60 || count==256)return -1;
                for(unsigned j=0;j<count;j++)if(calls[j].worker==worker && calls[j].serial==serial)return -1;
                calls[count++]=(struct pair_round_delivery){worker,serial,number,0,0,-1};
                if(number==231){terminal=1;exits++;}
            } else {
                if(!strcmp(kind,"returned")) {
                    if(sscanf(tail,"worker=%llu delivery=%llu cpu=%d value=%ld%n",&worker,&serial,&c,&value,&used)!=4 || tail[used] || c!=cpu || terminal)return -1;
                } else if(!strcmp(kind,"return_route")) {
                    if(sscanf(tail,"worker=%llu delivery=%llu launcher_cpu=%d guest_cpu=%d%n",&worker,&serial,&launcher,&c,&used)!=4 || tail[used] || c!=cpu || launcher<0 || launcher>1 || launcher==cpu || terminal)return -1;
                } else return -1;
                for(unsigned j=0;j<count;j++)if(calls[j].worker==worker && calls[j].serial==serial)d=&calls[j];
                if(!d || d->number==231 || d->returned)return -1;
                if(!strcmp(kind,"returned"))d->returned=1;
                else {if(d->routed)return -1;d->routed=1;d->launcher=launcher;}
            }
        } else if((mark=strstr(line,"application SCHEDULE "))) {
            if(sscanf(mark,"application SCHEDULE os=%u generation=%lu pid=%d cpu=%d%n",&osid,&generation,&found,&c,&used)!=4)return -1;
            if(found==pid){if(osid || generation!=1 || c!=cpu || mark[used] || ++schedules!=1)return -1;}
        } else if((mark=strstr(line,"application retirement "))) {
            unsigned long long token=0;int error=0;
            if(sscanf(mark,"application retirement os=%u generation=%lu pid=%d token=%llu errno=%d%n",&osid,&generation,&found,&token,&error,&used)!=5)return -1;
            if(found!=pid)continue;
            if(osid || generation!=1 || mark[used] || !terminal || acks!=1 || !token || last_errno==0 || (error!=-11 && error!=0) || ++attempts>12 || pair_seen_token_count==49152)return -1;
            for(unsigned j=0;j<pair_seen_token_count;j++)if(pair_seen_tokens[j]==token)return -1;
            pair_seen_tokens[pair_seen_token_count++]=token;last_errno=error;
        } else if((mark=strstr(line,"application_process=cleanup_requested "))) {
            int error=0;
            if(sscanf(mark,"application_process=cleanup_requested os=%u generation=%lu pid=%d intent_errno=%d%n",&osid,&generation,&found,&error,&used)!=4)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || error || ++releases!=1))return -1;
        } else if((mark=strstr(line,"application cleanup ACK "))) {
            unsigned long long token=0;int error=0,abandoned=-1;
            if(sscanf(mark,"application cleanup ACK os=%u generation=%lu pid=%d token=%llu errno=%d abandoned=%d%n",&osid,&generation,&found,&token,&error,&abandoned,&used)!=6)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || !token || error || (abandoned!=0 && abandoned!=1) || ++acks!=1))return -1;
        } else if((mark=strstr(line,"application procfs "))) {
            char op[16];int tid=-1;
            if(sscanf(mark,"application procfs %15s os=%u generation=%lu pid=%d tid=%d%n",op,&osid,&generation,&found,&tid,&used)!=5)return -1;
            if(found==pid) {
                if(osid || generation!=1 || tid<=0 || mark[used])return -1;
                if(strcmp(op,"published") && strcmp(op,"deleted"))return -1;
                /* Thread TIDs are genuine rows; only leader rows prove the
                 * original strict pair leader publication/deletion counts. */
                if(tid==pid) {if(!strcmp(op,"published"))published++;else deleted++;}
            }
        }
    }
    if(!count || exits!=1 || !attempts || last_errno || releases!=1 || acks!=1 || schedules!=1 || published!=1 || deleted!=1)return -1;
    for(unsigned j=0;j<count;j++)if(calls[j].number!=231) {
        if(!calls[j].returned)return -1;
        int slot=calls[j].routed?calls[j].launcher:cpu;
        for(unsigned k=0;k<j;k++)if(calls[k].worker==calls[j].worker && calls[k].number!=231 &&
            (calls[k].routed?calls[k].launcher:cpu)!=slot)return -1;
    }
    return 0;
}
#include "long_trace_retention.inc"
static int pair_round_gate(void)
{
    static char log[1048577];int n=long_kernel_snapshot(log,sizeof log-1);
    pair_fail_phase="kernel_snapshot";
    if(n<=0 || n==(int)sizeof log-1)return -1;
    log[n]=0;
    pair_fail_phase="stream_identity_oracle";
    if(pair_round_streams())return -1;
    pair_fail_phase="application_membership";
    /* No application from another PID/domain may hide between rounds. */
    for(const char *p=log;*p;p++)if(!strncmp(p,"application_syscall=",20) || !strncmp(p,"application SCHEDULE ",21)) {
        const char *end=strchr(p,'\n'),*id=strstr(p," pid=");int pid=0;unsigned j=0;
        if(!id || (end && id>=end) || sscanf(id," pid=%d",&pid)!=1)return -1;
        for(;j<(unsigned)pair_seen_pid_count;j++)if(pair_seen_pids[j]==pid)break;
        if(j==(unsigned)pair_seen_pid_count)return -1;
    }
    for(int i=0;i<2;i++){pair_fail_phase=i?"app1_trace_oracle":"app0_trace_oracle";if(pair_round_trace(log,pair_results[i].pid,i))return -1;}
    pair_fail_phase="trace_retention";
    return pair_trace_save(log,(size_t)n);
}
