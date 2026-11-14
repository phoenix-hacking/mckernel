#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>

/* Only fixture path/metadata/control surfaces are replaced. No real ioctl,
 * klog, mount, module, guest or reboot operation is invoked by this program. */
static int fixture_open(const char *, int, ...);
static int fixture_fstat(int, struct stat *);
static ssize_t fixture_random(void *, size_t, unsigned int);
static int fixture_klog(int, char *, int);
static int fixture_ioctl(int, unsigned long, ...);
#define open fixture_open
#define fstat fixture_fstat
#define getrandom fixture_random
#define klogctl fixture_klog
#define ioctl fixture_ioctl
#define main retained_production_collector_main
#include "collector-helper-failure-context-pair-boot.c"
#undef main
#undef open
#undef fstat
#undef getrandom
#undef klogctl
#undef ioctl

static char directory[PATH_MAX];
static int fd_kind[256], ownership_bad, log_generation=1;
static int payload_calls, helper_calls;
static jmp_buf helper_failure;
static struct pair_assignment pair_boot_assignment;
static char pair_boot_log[PAIR_LOG_LIMIT];

static const char *map_path(const char *path)
{
    const char *leaf=NULL;
    if(!strcmp(path,PAIR_CHALLENGE))leaf="challenge";
    if(!strcmp(path,PAIR_ASSIGNMENT))leaf="assignment";
    if(!strcmp(path,"/dev/mcos0"))leaf="device";
    if(!strcmp(path,"/dev/kmsg"))leaf="kmsg";
    if(!strcmp(path,"/sys/devices/system/cpu/online"))leaf="online";
    if(!strcmp(path,"/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors"))leaf="count";
    if(!strcmp(path,"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online"))leaf="cpu0";
    if(!strcmp(path,"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online"))leaf="cpu1";
    assert(leaf);static char mapped[PATH_MAX];
    int n=snprintf(mapped,sizeof mapped,"%s/%s",directory,leaf);
    assert(n>0 && (size_t)n<sizeof mapped);return mapped;
}
static int fixture_open(const char *path,int flags,...)
{
    mode_t mode=0;
    if(flags&O_CREAT){va_list ap;va_start(ap,flags);mode=(mode_t)va_arg(ap,int);va_end(ap);}
    int fd=open(map_path(path),flags,mode);
    if(fd>=0){assert(fd<256);fd_kind[fd]=!strcmp(path,PAIR_ASSIGNMENT)?1:!strcmp(path,"/dev/mcos0")?2:0;}
    return fd;
}
static int fixture_fstat(int fd,struct stat *s)
{
    int rc=fstat(fd,s);
    if(!rc && fd_kind[fd]==1){s->st_uid=ownership_bad?1:0;s->st_gid=0;}
    if(!rc && fd_kind[fd]==2)s->st_mode=(s->st_mode&07777)|S_IFCHR;
    return rc;
}
static ssize_t fixture_random(void *p,size_t n,unsigned int flags)
{
    assert(flags==GRND_NONBLOCK && n==16);
    const unsigned long nonce[2]={0x1234567812345678UL,0x7654321076543210UL};
    memcpy(p,nonce,n);return (ssize_t)n;
}
static int fixture_klog(int type,char *p,int n)
{
    assert(type==3);
    int size=snprintf(p,(size_t)n,
        "IHK-SMP: control accepted os=0 generation=%d port=501 guest_cpu=0 linux_cpu=1 cookie=1\n"
        "IHK-SMP: control accepted os=0 generation=%d port=501 guest_cpu=1 linux_cpu=2 cookie=2\n",
        log_generation,log_generation);
    assert(size>0 && size<n);return size;
}
static int fixture_ioctl(int fd,unsigned long request,...)
{
    assert(fd>=0 && fd_kind[fd]==2 && request==0x30a02907);return 2;
}

#define SYS_OPEN 2
#define SYS_READ 0
#define SYS_WRITE 1
#define SYS_IOCTL 16
static long fixture_boot_call(long nr,long a,long b,long c)
{
    long rc;
    if(nr==SYS_OPEN)rc=fixture_open((const char*)a,(int)b,(int)c);
    else if(nr==SYS_READ)rc=read((int)a,(void*)b,(size_t)c);
    else if(nr==SYS_WRITE)rc=write((int)a,(const void*)b,(size_t)c);
    else if(nr==SYS_IOCTL){assert(b==0x30a02907);return 2;}
    else if(nr==103)return fixture_klog((int)a,(char*)b,(int)c);
    else abort();
    return rc<0?-errno:rc;
}
static void fixture_close(long fd){assert(close((int)fd)==0);}
#define call fixture_boot_call
#define close_fd fixture_close
#define require(test) do{if(!(test))longjmp(helper_failure,1);}while(0)
#include "actual-native-boot-challenge-and-publish.inc"
#undef require
#undef close_fd
#undef call

static int actual_helper(void)
{
    memset(&pair_boot_assignment,0,sizeof pair_boot_assignment);
    if(setjmp(helper_failure))return -1;
    pair_boot_challenge();
    /* Fixture substitutes only the already qualified hardware assignment.
     * The actual helper publication/parser and collector discovery execute. */
    pair_boot_assignment.count=2;
    pair_boot_assignment.physical[0]=1;pair_boot_assignment.physical[1]=2;
    pair_boot_publish(0);
    return 0;
}
static int fixture_helper(const char *tag,const char *path,char *const av[],int *safe)
{
    (void)safe;helper_calls++;
    assert(!strcmp(tag,"boot") && !strcmp(path,"/bin/native-boot"));
    assert(!strcmp(av[0],path) && !strcmp(av[1],"hidos") && !strcmp(av[2],"allow_oversubscribe") && !av[3]);
    return actual_helper();
}
static void fixture_supervise(const char *path,char *const av[],char *const env[],
                             const char *cwd,unsigned timeout,struct result *r)
{
    (void)av;(void)env;(void)r;
    assert(!strcmp(path,"/bin/mcexec") && !strcmp(cwd,"/case/work") && timeout==10000);
    assert(pair_generation==1 && pair_os==0 && pair_host_cpus[0]==1 && pair_host_cpus[1]==2);
    payload_calls++;
}
#define helper fixture_helper
#define supervise fixture_supervise
static int actual_collector_sequence(void)
{
    int good=1,safe=1;struct result payload;
#include "actual-collector-boot-sequence.inc"
finish:return good?0:-1;
}
static int original_collector_sequence(void)
{
    int good=1,safe=1;struct result payload;
#include "original-collector-boot-sequence.inc"
finish:return good?0:-1;
}
#undef helper
#undef supervise

static void put_file(const char *path,const void *raw,size_t n)
{
    int fd=open(path,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0600);assert(fd>=0);
    assert(write(fd,raw,n)==(ssize_t)n);assert(close(fd)==0);
}
static void new_case(const char *root,int index)
{
    int n=snprintf(directory,sizeof directory,"%s/case-%02d",root,index);
    assert(n>0 && (size_t)n<sizeof directory && mkdir(directory,0700)==0);
    ownership_bad=0;log_generation=1;payload_calls=helper_calls=0;
    put_file(map_path("/dev/mcos0"),"",0);put_file(map_path("/dev/kmsg"),"",0);
    put_file(map_path("/sys/devices/system/cpu/online"),"0,3\n",4);
    put_file(map_path("/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors"),"2\n",2);
    put_file(map_path("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online"),"1\n",2);
    put_file(map_path("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online"),"1\n",2);
}
static struct pair_assignment proof(void)
{
    struct pair_assignment a;int fd=open(map_path(PAIR_ASSIGNMENT),O_RDONLY);
    assert(fd>=0 && read(fd,&a,sizeof a)==sizeof a && close(fd)==0);return a;
}
int main(int argc,char **argv)
{
    assert(argc==2 && mkdir(argv[1],0700)==0);int cpus[2]={-1,-1};
    new_case(argv[1],0);assert(original_collector_sequence()==-1 && helper_calls==1 && !payload_calls);
    new_case(argv[1],1);assert(actual_collector_sequence()==0 && helper_calls==1 && payload_calls==1);
    assert(pair_prepare_challenge()==-1); /* Existing challenge never replaced. */
    new_case(argv[1],2);assert(actual_helper()==-1); /* Exact missing challenge. */
    new_case(argv[1],3);assert(pair_prepare_challenge()==0);assert(truncate(map_path(PAIR_CHALLENGE),15)==0);assert(actual_helper()==-1);
    new_case(argv[1],4);assert(pair_prepare_challenge()==0);assert(truncate(map_path(PAIR_CHALLENGE),17)==0);assert(actual_helper()==-1);
    new_case(argv[1],5);assert(pair_prepare_challenge()==0 && pair_discover(cpus)==77);
    for(int i=6;i<12;i++){
        new_case(argv[1],i);assert(pair_prepare_challenge()==0 && actual_helper()==0);
        struct pair_assignment a=proof();
        if(i==6)assert(truncate(map_path(PAIR_ASSIGNMENT),47)==0);
        if(i==7){a.nonce[0]^=1;put_file(map_path(PAIR_ASSIGNMENT),&a,sizeof a);}
        if(i==8){a.generation=0;put_file(map_path(PAIR_ASSIGNMENT),&a,sizeof a);}
        if(i==9)log_generation=2;
        if(i==10){a.physical[1]=3;put_file(map_path(PAIR_ASSIGNMENT),&a,sizeof a);}
        if(i==11)ownership_bad=1;
        assert(pair_discover(cpus)==77);
    }
    puts("{\"status\":\"PASS_ACTUAL_COLLECTOR_AND_4312_CHALLENGE_DISCOVERY_BODY_ONLY\",\"cases\":12,\"original_missing_challenge_refused\":true,\"actual_sequence_positive\":true,\"private_fixture_only\":true,\"real_ioctl_calls\":0,\"guest_runs\":0}");
    return 0;
}
