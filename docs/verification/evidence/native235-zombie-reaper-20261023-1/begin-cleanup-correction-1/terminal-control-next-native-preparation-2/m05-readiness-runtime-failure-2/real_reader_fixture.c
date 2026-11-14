/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact retained reader, save_file/O_EXCL and procfs directory reader, with only
 * kernel-log acquisition, clock/sleep and /case,/proc path translation controlled.
 * No klog syscall, ioctl, probe, module, guest or privileged path is used. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#define REBOOT_LOG_LIMIT 262144u
#define MS 1000000ull
static unsigned assertions, reads, opens, eexist;
static uint64_t clock_ns=1000000;
static char pending[REBOOT_LOG_LIMIT], positive[REBOOT_LOG_LIMIT];
static const char *mode;
static unsigned provider_epoch=1;
static struct stat first_identity[2];
static void need(int ok,const char *why) {
 ++assertions;if(!ok){fprintf(stderr,"FAIL %s errno=%d reads=%u opens=%u\n",why,errno,reads,opens);exit(1);}
}
static size_t load(const char *name,char *out) {
 FILE *f=fopen(name,"rb");need(f!=NULL,"retained real-file input");
 size_t n=fread(out,1,REBOOT_LOG_LIMIT-1,f);
 need(!ferror(f) && feof(f),"bounded complete fixture input");
 need(fclose(f)==0,"input close");out[n]=0;return n;
}
static uint64_t now_ns(void) {clock_ns+=1000;return clock_ns;}
static uint64_t bounded_deadline(uint64_t requested,uint64_t reserve) {(void)reserve;return requested;}
#include "actual-write_all.c.inc"
static int private_open(const char *path,int flags,mode_t permissions) {
 const char *prefix="/case/evidence/";
 need(strncmp(path,prefix,strlen(prefix))==0 && strchr(path+strlen(prefix),'/')==NULL,"exact private evidence translation");
 char local[160];need(snprintf(local,sizeof local,"evidence/%s",path+strlen(prefix))<(int)sizeof local,"private evidence path bound");
 ++opens;int fd=open(local,flags,permissions);if(fd<0 && errno==EEXIST)++eexist;return fd;
}
#define open private_open
#include "actual-save_file.c.inc"
#undef open
static DIR *private_opendir(const char *path) {
 need(!strcmp(path,"/proc/mcos0"),"exact procfs path");
 return opendir(!strcmp(mode,"missing-procfs")?"missing-mcos":"mcos");
}
#define opendir private_opendir
#include "actual-retired_at.c.inc"
#undef opendir
static int klogctl(int action,char *out,int length) {
 need(action==3 && length==REBOOT_LOG_LIMIT,"read-only bounded controlled log provider");++reads;
 if(!strcmp(mode,"read-error")){errno=EIO;return -1;}
 if(!strcmp(mode,"arrival") && reads==2) {
  char path[96];snprintf(path,sizeof path,"evidence/begin-readiness-%u.kmsg",provider_epoch);
  need(stat(path,&first_identity[provider_epoch-1])==0,"first immutable snapshot inode captured before third poll");
 }
 const char *text=!strcmp(mode,"arrival") && reads>=3?positive:pending;
 size_t n=strlen(text);memcpy(out,text,n);return (int)n;
}
#include "actual-reboot-snapshot.c.inc"
#ifdef ORIGINAL
#include "original-readiness-glue.c.inc"
#else
#include "actual-readiness-glue.c.inc"
#endif
static int controlled_nanosleep(const struct timespec *t,void *unused) {
 (void)unused;clock_ns+=(uint64_t)t->tv_sec*1000000000ull+t->tv_nsec;return 0;
}
#define nanosleep controlled_nanosleep
static int original_main_loop(void) {int empty=0;
#include "actual-main-readiness-loop.c.inc"
 return empty;
}
static int original_second_loop(void) {int value=0,*empty=&value;
#include "actual-second-readiness-loop.c.inc"
 return value;
}
static void verify_snapshots(void) {
 char path[96];struct stat current;static char bytes[REBOOT_LOG_LIMIT];
 snprintf(path,sizeof path,"evidence/begin-readiness-%u.kmsg",provider_epoch);
 need(stat(path,&current)==0,"first snapshot still present");
 struct stat *first=&first_identity[provider_epoch-1];
 need(current.st_dev==first->st_dev && current.st_ino==first->st_ino &&
      current.st_size==first->st_size && current.st_mtim.tv_sec==first->st_mtim.tv_sec &&
      current.st_mtim.tv_nsec==first->st_mtim.tv_nsec,"first pending snapshot inode and content metadata unchanged");
 load(path,bytes);need(!strcmp(bytes,pending),"first pending snapshot exact retained bytes");
 snprintf(path,sizeof path,"evidence/begin-readiness-%u-terminal.kmsg",provider_epoch);
 load(path,bytes);need(!strcmp(bytes,positive),"terminal snapshot exact controlled final0 bytes");
 need(stat(path,&current)==0 && (current.st_dev!=first->st_dev || current.st_ino!=first->st_ino),"first and terminal snapshot inodes distinct");
}
static unsigned count_snapshots(void) {
 DIR *dir=opendir("evidence");need(dir!=NULL,"real output directory read");unsigned count=0;struct dirent *row;
 while((row=readdir(dir)))if(row->d_name[0]!='.')++count;
 need(closedir(dir)==0,"output directory close");return count;
}
int main(int argc,char **argv) {
 need(argc==4,"explicit mode and two epoch inputs");mode=argv[1];(void)reboot_snapshot;
 load(argv[2],pending);strcpy(positive,pending);
 const char *final="<6>[   33.129164] ihk_smp_x86_64: IHK-SMP: application retirement os=0 generation=1 pid=256 token=22 errno=0\n";
 need(strlen(positive)+strlen(final)<sizeof positive,"controlled append bound");strcat(positive,final);
 need(mkdir("evidence",0700)==0 && mkdir("mcos",0700)==0,"fresh private real directories");
 need(m05_begin_ready((unsigned char*)pending,strlen(pending),1)==0,"retained7589 parsed pending, not malformed");
 need(m05_begin_ready((unsigned char*)positive,strlen(positive),1)==1,"only explicitly controlled final0 makes complete lifecycle ready");
 uint64_t beginning=clock_ns;int state;
 if(!strcmp(mode,"original-collision")) {
  need(begin_retired_at("/proc/mcos0",1)==0,"original first poll pending");
  state=begin_retired_at("/proc/mcos0",1);
  need(state==-1 && eexist==1 && reads==2 && count_snapshots()==1,"original poll two actual O_EXCL EEXIST counterexample");
  need(clock_ns-beginning<1000000000ull,"original reader aborts before one second");
 } else if(!strcmp(mode,"collision")) {
  int fd=open("evidence/begin-readiness-1.kmsg",O_WRONLY|O_CREAT|O_EXCL,0600);
  need(fd>=0 && write(fd,"KEEP",4)==4 && close(fd)==0,"owned preexisting snapshot");
  need(begin_retired_at("/proc/mcos0",1)==-1 && eexist==1,"actual collision still fails closed");
  char bytes[8]={0};fd=open("evidence/begin-readiness-1.kmsg",O_RDONLY);
  need(fd>=0 && read(fd,bytes,sizeof bytes)==4 && close(fd)==0 && !strcmp(bytes,"KEEP"),"preexisting bytes preserved");
 } else if(!strcmp(mode,"missing-procfs")) {
  need(begin_retired_at("/proc/mcos0",1)==-1 && reads==0 && opens==0,"real missing procfs fails before reader");
 } else if(!strcmp(mode,"read-error")) {
  need(begin_retired_at("/proc/mcos0",1)==-1 && reads==1 && opens==0,"reader error remains fatal");
 } else if(!strcmp(mode,"nonempty-procfs")) {
  need(mkdir("mcos/256",0700)==0,"real numeric procfs surrogate");
  need(begin_retired_at("/proc/mcos0",1)==0 && reads==0 && opens==0,"nonempty real directory blocks readiness without snapshot");
 } else {
  state=original_main_loop();
  if(!strcmp(mode,"arrival")) {
   need(state==1 && reads==3 && opens==2 && eexist==0 && count_snapshots()==2,"actual reader advances only on controlled final0 after two pending polls");
   verify_snapshots();provider_epoch=2;reads=0;
   load(argv[3],pending);strcpy(positive,pending);
   strcat(positive,"<6>[   34.129164] ihk_smp_x86_64: IHK-SMP: application retirement os=0 generation=2 pid=258 token=42 errno=0\n");
   need(m05_begin_ready((unsigned char*)pending,strlen(pending),2)==0,"controlled epoch2 pending, prior retirement0 cannot authorize");
   need(m05_begin_ready((unsigned char*)positive,strlen(positive),2)==1,"controlled epoch2 own retirement0 required");
   state=original_second_loop();
   need(state==1 && reads==3 && opens==4 && eexist==0 && count_snapshots()==4,"epoch2 actual reader saves only first and terminal after two pending polls");
   verify_snapshots();
  } else {
   need(!strcmp(mode,"pending"),"known fixture mode");
   need(state==0 && reads>50 && opens==1 && eexist==0 && count_snapshots()==1,"actual five-second loop keeps pending snapshots until deadline without final0");
   need(clock_ns-beginning>=5000*MS,"unchanged original five-second deadline exhausted");
  }
 }
 printf("PASS mode=%s assertions=%u reads=%u saved=%u eexist=%u controlled_elapsed_ns=%llu native_acceptance=false\n",mode,assertions,reads,count_snapshots(),eexist,(unsigned long long)(clock_ns-beginning));
 return 0;
}
