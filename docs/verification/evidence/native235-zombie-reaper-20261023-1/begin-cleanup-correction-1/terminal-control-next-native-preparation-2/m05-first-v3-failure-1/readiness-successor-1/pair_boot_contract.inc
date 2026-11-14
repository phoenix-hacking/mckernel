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
