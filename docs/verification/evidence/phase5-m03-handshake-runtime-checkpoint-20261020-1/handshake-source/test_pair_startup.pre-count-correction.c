#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/klog.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>
#include "candidate/pair_assignment.h"
enum {VALID, RNG_SHORT, RNG_ZERO, SAVE_FAIL, MISSING, SHORT, TAIL, OWNER,
 GROUP, LINKS, MODE, SIZE, TYPE, STAT, NONCE, CPU, COUNT, OS, GENERATION,
 STALE_LOG, DUP_ROUTE, CAPACITY, LINUX_CPU, MC_CPU, MC_COUNT, KLOG_FULL, CAPACITY_SECOND, CLOSE_FAIL};
static int vector, prepared, booted, read_index, ioctl_calls;
static struct pair_assignment assignment;
static unsigned reads[4];
static ssize_t fake_random(void *p,size_t n,unsigned f)
{
 assert(!prepared && !booted && n==16 && f==GRND_NONBLOCK);
 unsigned long a[2]={11,22};if(vector==RNG_ZERO)a[0]=a[1]=0;
 memcpy(p,a,n);return vector==RNG_SHORT?15:16;
}
static int save_file(const char *p,const void *b,size_t n)
{
 assert(!strcmp(p,PAIR_CHALLENGE) && n==16 && !booted);
 if(vector==SAVE_FAIL){errno=EEXIST;return -1;}
 assignment=(struct pair_assignment){PAIR_MAGIC,{0,0},0,2,9,{1,2}};
 memcpy(assignment.nonce,b,16);prepared=1;return 0;
}
static int fake_open(const char *p,int flags,...)
{
 assert(prepared && booted);assert((flags&(O_NOFOLLOW|O_CLOEXEC))==(O_NOFOLLOW|O_CLOEXEC));
 if(!strcmp(p,PAIR_ASSIGNMENT)) {assert(flags&O_NONBLOCK);if(vector==MISSING){errno=ENOENT;return -1;}return 10;}
 if(!strcmp(p,"/dev/mcos0"))return 11;
 if(!strcmp(p,"/sys/devices/system/cpu/online"))return 12;
 if(!strcmp(p,"/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors"))return 13;
 if(!strcmp(p,"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online"))return 14;
 if(!strcmp(p,"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online"))return 15;
 assert(0);return -1;
}
static int fake_stat(int fd,struct stat *s)
{
 memset(s,0,sizeof *s);s->st_mode=fd==10?S_IFREG|0600:S_IFCHR|0600;
 s->st_nlink=1;s->st_size=48;
 if(fd!=10)return 0;
 if(vector==STAT)return -1;
 if(vector==OWNER)s->st_uid=1;
 if(vector==GROUP)s->st_gid=1;
 if(vector==LINKS)s->st_nlink=2;
 if(vector==MODE)s->st_mode|=0040;
 if(vector==SIZE)s->st_size=47;
 if(vector==TYPE)s->st_mode=S_IFIFO|0600;
 return 0;
}
static ssize_t fake_read(int fd,void *p,size_t n)
{
 if(fd==10){
  if(read_index++)return vector==TAIL?1:0;
  assert(n==48);struct pair_assignment a=assignment;
  if(vector==NONCE)a.nonce[0]++;
  if(vector==CPU)a.physical[1]=3;
  if(vector==COUNT)a.count=1;
  if(vector==OS)a.os=1;
  if(vector==GENERATION)a.generation=0;
  memcpy(p,&a,sizeof a);return vector==SHORT?47:48;
 }
 unsigned i=(unsigned)(fd-12);assert(i<4);
 if(reads[i]++%2)return 0;
 const char *v=fd==12?"0,3\n":fd==13?"2\n":"1\n";
 if((vector==LINUX_CPU && fd==12)||(vector==MC_COUNT && fd==13)||(vector==MC_CPU && fd==15))v="9\n";
 size_t z=strlen(v);assert(z<=n);memcpy(p,v,z);return (ssize_t)z;
}
static int fake_close(int fd){return vector==CLOSE_FAIL&&fd==10?-1:0;}
static int fake_ioctl(int fd,unsigned long op,...)
{assert(fd==11&&op==0x30a02907);ioctl_calls++;return vector==CAPACITY || (vector==CAPACITY_SECOND&&ioctl_calls==2)?3:2;}
static int fake_klog(int action,char *p,int n)
{
 assert(action==3&&n==PAIR_LOG_LIMIT);
 if(vector==KLOG_FULL)return n;
 const char *log="IHK-SMP: control accepted os=0 generation=9 port=501 guest_cpu=0 linux_cpu=1 cookie=x\nIHK-SMP: control accepted os=0 generation=9 port=501 guest_cpu=1 linux_cpu=2 cookie=x\n";
 if(vector==STALE_LOG)log="IHK-SMP: control accepted os=0 generation=8 port=501 guest_cpu=0 linux_cpu=1 cookie=x\nIHK-SMP: control accepted os=0 generation=8 port=501 guest_cpu=1 linux_cpu=2 cookie=x\n";
 if(vector==DUP_ROUTE)log="IHK-SMP: control accepted os=0 generation=9 port=501 guest_cpu=0 linux_cpu=1 cookie=x\nIHK-SMP: control accepted os=0 generation=9 port=501 guest_cpu=0 linux_cpu=1 cookie=x\n";
 memcpy(p,log,strlen(log));return (int)strlen(log);
}
#define getrandom fake_random
#define open fake_open
#define fstat fake_stat
#define read fake_read
#define close fake_close
#define ioctl fake_ioctl
#define klogctl fake_klog
#include "candidate/nd_pair_startup.h"
int main(void)
{
 for(vector=VALID;vector<=CLOSE_FAIL;vector++) {
  prepared=booted=read_index=ioctl_calls=0;memset(reads,0,sizeof reads);
  int r=pair_prepare_challenge();
  if(vector>=RNG_SHORT&&vector<=SAVE_FAIL){assert(r==-1&&!prepared);continue;}
  assert(r==0&&prepared);booted=1;int cpus[2]={-1,-1};r=pair_discover(cpus);
  if(vector==VALID)assert(r==0&&cpus[0]==0&&cpus[1]==1&&ioctl_calls==2);
  else assert(r==77&&cpus[0]==-1&&cpus[1]==-1);
 }
 puts("PASS 29 actual startup-header vectors; mocked Linux resources, zero boots/apps");
 return 0;
}
