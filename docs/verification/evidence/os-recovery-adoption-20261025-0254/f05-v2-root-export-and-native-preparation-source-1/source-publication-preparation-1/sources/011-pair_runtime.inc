#include <sys/ioctl.h>
static int pair_host_cpus[2];
static int pair_read_value(const char *path,const char *expected)
{
    char b[32];int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return -1;
    ssize_t n=read(fd,b,sizeof b);int ok=n==(ssize_t)strlen(expected) && !memcmp(b,expected,(size_t)n);
    if(ok)ok=read(fd,b,sizeof b)==0;
    if(close(fd))ok=0;
    return ok?0:-1;
}
#include <sys/random.h>
#include "pair_assignment.h"
static unsigned long pair_nonce[2];
static unsigned long pair_generation;
static unsigned int pair_os;
static int pair_prepare_challenge(void)
{
    ssize_t n=getrandom(pair_nonce,sizeof pair_nonce,GRND_NONBLOCK);
    if(n!=(ssize_t)sizeof pair_nonce || !(pair_nonce[0]||pair_nonce[1]))return -1;
    return save_file(PAIR_CHALLENGE,pair_nonce,sizeof pair_nonce);
}
static int pair_discover(int cpus[2])
{
    struct pair_assignment a;char tail;struct stat s;
    int proof=open(PAIR_ASSIGNMENT,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if(proof<0)return 77;
    int ok=fstat(proof,&s)==0 && S_ISREG(s.st_mode) && s.st_uid==0 && s.st_gid==0 &&
        s.st_nlink==1 && (s.st_mode&07777)==0600 && s.st_size==(off_t)sizeof a;
    if(ok)ok=read(proof,&a,sizeof a)==(ssize_t)sizeof a && read(proof,&tail,1)==0 &&
        pair_assignment_valid(&a,pair_nonce);
    if(close(proof))ok=0;
    if(!ok)return 77;
    char log[PAIR_LOG_LIMIT];unsigned long generation=0;
    int n=klogctl(3,log,sizeof log);
    if(n<=0 || n==(int)sizeof log || pair_routes(log,(unsigned long)n,&a,&generation) ||
       generation!=a.generation)return 77;
    int fd=open("/dev/mcos0",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return 77;
    ok=fstat(fd,&s)==0 && S_ISCHR(s.st_mode) && ioctl(fd,0x30a02907,0)==2;
    if(ok)ok=pair_read_value("/sys/devices/system/cpu/online","0,3\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors","2\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online","1\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online","1\n")==0;
    if(ok)ok=ioctl(fd,0x30a02907,0)==2;
    if(close(fd))ok=0;
    if(!ok)return 77;
    pair_host_cpus[0]=a.physical[0];pair_host_cpus[1]=a.physical[1];
    pair_generation=a.generation;pair_os=a.os;
    cpus[0]=0;cpus[1]=1; /* matched exact-generation kernel501 rank records */
    return 0;
}
static struct result pair_results[2];
static int pair_load_results(void)
{
    for(int i=0;i<2;i++) {
        char p[128];snprintf(p,sizeof p,"/case/evidence/app%d.result",i);
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
