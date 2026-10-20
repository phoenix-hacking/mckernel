static struct result pair_results[2];
static int pair_load_results(void)
{
    for(int i=0;i<2;i++) {
#if defined(ND_PAIR_TWO_ROUNDS)
        char p[PATH_MAX];snprintf(p,sizeof p,"%s/app%d.result",pair_evidence_dir,i);
#else
        char p[128];snprintf(p,sizeof p,"/case/evidence/app%d.result",i);
#endif
        int fd=open(p,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);if(fd<0)return -1;
        struct stat s;int ok=!fstat(fd,&s) && S_ISREG(s.st_mode) && s.st_size==(off_t)sizeof(struct result);
        size_t pos=0;while(ok && pos<sizeof(struct result)) {
            ssize_t n=read(fd,(char*)&pair_results[i]+pos,sizeof(struct result)-pos);
            if(n>0)pos+=(size_t)n;else if(n<0 && errno==EINTR)continue;else ok=0;
        }
        if(close(fd))ok=0;
        if(!ok || pair_results[i].out.kept>STREAM_LIMIT || pair_results[i].err.kept>STREAM_LIMIT)return -1;
    }
    return 0;
}
static int publish_pair(int fd,int empty)
{
    char b[FRAME_LIMIT];size_t n=0;
    if(append(b,&n,"ND_PAIR {\"os\":%u,\"generation\":%lu,\"host_cpus\":[%d,%d],\"cpus\":[0,1],\"procfs_empty\":%s,\"apps\":[",pair_os,pair_generation,pair_host_cpus[0],pair_host_cpus[1],empty?"true":"false"))return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        if(append(b,&n,"%s{\"id\":%d,\"pid\":%d,\"cpu\":%d,\"cwd\":\"/case/two-app/work%d\",\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"-c\",\"%d\",\"0\",\"/apps/app%d\"],\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\",\"PAIR_CPU\":\"%d\"},\"raw_wait_status\":%d,\"clean\":%d,\"fault\":%d,\"timeout\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu,\"streams\":{\"stdout\":",i?",":"",i,r->pid,i,i,i,i,i,r->status,r->clean,r->fault,r->timeout,(unsigned long long)r->started,(unsigned long long)r->reaped,(unsigned long long)r->finished) ||
           stream_json(b,&n,&r->out) || append(b,&n,",\"stderr\":") || stream_json(b,&n,&r->err) || append(b,&n,"}}"))return -1;
    }
    if(append(b,&n,"]}\n"))return -1;
    return write_all(fd,b,n);
}
