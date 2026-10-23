/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#define MAX 262144u
#define REBOOT_LOG_LIMIT MAX
#define MS 1000000ull
extern int m05_begin_ready(const unsigned char *,size_t,uint64_t);
static char base[MAX], positive[MAX], second_pending[MAX],second_positive[MAX],whole_fail[MAX];
static const char final1[]="<6>[   33.309450] ihk_smp_x86_64: IHK-SMP: application retirement os=0 generation=1 pid=254 token=22 errno=0\n";
static const char final2[]="<6>[   34.309450] ihk_smp_x86_64: IHK-SMP: application retirement os=0 generation=2 pid=258 token=42 errno=0\n";
static unsigned checks,reads,append_after,proc_calls,save_calls;
static int proc_state=1,read_error,save_error,full_read;
static const char *pending,*ready;
static uint64_t clock_ns=1;
static void need(int ok,const char *why) {++checks;if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
static size_t load(const char *path,char *b) {FILE*f=fopen(path,"rb");if(!f)abort();size_t n=fread(b,1,MAX-1,f);if(ferror(f)||!feof(f))abort();fclose(f);b[n]=0;return n;}
static int klogctl(int action,char *bytes,int length) {
 need(action==3 && length==MAX,"read-only bounded klog acquisition");++reads;
 if(read_error){errno=EIO;return -1;}if(full_read){memset(bytes,'X',MAX);return MAX;}
 const char *text=append_after && reads>=append_after?ready:pending;size_t n=strlen(text);memcpy(bytes,text,n);return (int)n;
}
static int save_file(const char *name,const void *bytes,size_t count) {
 (void)bytes;++save_calls;need(count<=MAX,"bounded retained snapshot");
 need(strstr(name,"/case/evidence/")!=NULL,"existing owned evidence root");return save_error?-1:0;
}
static int retired_at(const char *path) {need(!strcmp(path,"/proc/mcos0"),"exact procfs path");++proc_calls;return proc_state;}
#include "actual-reboot-snapshot.c.inc"
#include "actual-readiness-glue.c.inc"
static uint64_t now_ns(void) {clock_ns+=MS;return clock_ns;}
static uint64_t bounded_deadline(uint64_t n,uint64_t reserve) {(void)reserve;return n;}
static int fixture_nanosleep(const struct timespec *t,void *unused) {(void)unused;clock_ns+=(uint64_t)t->tv_sec*1000000000ull+t->tv_nsec;return 0;}
#define nanosleep fixture_nanosleep
static int first_loop(void) {int empty=0;
#include "actual-main-readiness-loop.c.inc"
 return empty;
}
static int second_loop(void) {int value=0,*empty=&value;
#include "actual-second-readiness-loop.c.inc"
 return value;
}
static void replace(char*out,const char*source,const char*from,const char*to) {
 const char *at=strstr(source,from);if(!at)abort();size_t pre=(size_t)(at-source);if(pre+strlen(to)+strlen(at+strlen(from))>=MAX)abort();memcpy(out,source,pre);strcpy(out+pre,to);strcat(out,at+strlen(from));
}
static void rejects(const char *text,uint64_t epoch,const char *name) {need(m05_begin_ready((const unsigned char*)text,strlen(text),epoch)!=1,name);}
int main(void) {
 load("retained-pre-shutdown.kmsg",base);load("retained-full-failure.serial",whole_fail);
 strcpy(positive,base);strcat(positive,final1);
 need(m05_begin_ready((unsigned char*)base,strlen(base),1)==0,"retained495e is not retirement-ready");
 need(m05_begin_ready((unsigned char*)positive,strlen(positive),1)==1,"controlled appended same-domain retirement0");
 rejects(whole_fail,1,"actual post-effect failed shutdown cannot be retried");
 static char changed[MAX];
 load("controlled-ACK-before-intent.kmsg",changed);need(m05_begin_ready((unsigned char*)changed,strlen(changed),1)==1,"real ACK may log before intent");

 replace(changed,positive,"pid=254 token=22 errno=0","pid=255 token=22 errno=0");rejects(changed,1,"foreign PID");
 replace(changed,positive,"generation=1 pid=254 token=22 errno=0","generation=2 pid=254 token=22 errno=0");rejects(changed,1,"foreign generation");
 replace(changed,positive,"pid=254 token=22 errno=0","pid=254 token=3 errno=0");need(m05_begin_ready((unsigned char*)changed,strlen(changed),1)==1,"ACK and query token namespaces may share numeric value");
 replace(changed,positive,"pid=254 token=22 errno=0","pid=254 token=21 errno=0");rejects(changed,1,"duplicate EAGAIN token");
 replace(changed,positive,"pid=254 token=22 errno=0","pid=254 token=0 errno=0");rejects(changed,1,"zero token");
 replace(changed,positive,"pid=254 token=22 errno=0","pid=254 token=18446744073709551616 errno=0");rejects(changed,1,"overflow token");
 replace(changed,positive,"pid=254 token=22 errno=0","pid=254 token=22 errno=-11");rejects(changed,1,"EAGAIN alone");
 replace(changed,positive,"pid=254 token=3 errno=0","pid=254 token=3 errno=-16");rejects(changed,1,"failed real ACK");
 replace(changed,positive,"pid=254 token=3 errno=0","pid=255 token=3 errno=0");rejects(changed,1,"foreign ACK PID");
 replace(changed,positive,"pid=254 intent_errno=0","pid=254 intent_errno=-16");rejects(changed,1,"failed intent");
 replace(changed,positive,"pid=254 tid=254","pid=254 tid=255");rejects(changed,1,"wrong publication TID");
 replace(changed,positive,"application procfs deleted os=0 generation=1 pid=254 tid=254","application procfs deleted os=0 generation=1 pid=254 tid=255");rejects(changed,1,"wrong DELETE TID");
 replace(changed,positive,"delivery=20 cpu=0 number=231","delivery=20 cpu=0 number=7");rejects(changed,1,"no exit231");
 replace(changed,positive,"application SCHEDULE os=0 generation=1 pid=254 cpu=0","application SCHEDULE os=0 generation=1 pid=254 cpu=1");rejects(changed,1,"wrong scheduled CPU");
 replace(changed,positive,"application SCHEDULE os=0 generation=1 pid=254 cpu=0","application SCHEDULE os=0 generation=2 pid=254 cpu=0");rejects(changed,1,"no current schedule");
 strcpy(changed,final1);strcat(changed,base);rejects(changed,1,"retirement0 before schedule/ACK/DELETE");
 strcpy(changed,positive);strcat(changed,final1);rejects(changed,1,"duplicate final retirement0");
 strcpy(changed,positive);strcat(changed,"<6>[ 34.000000] ihk_smp_x86_64: IHK-SMP: application SCHEDULE os=0 generation=1 pid=255 cpu=0\n");rejects(changed,1,"second scheduled identity");
 strcpy(changed,positive);changed[strlen(changed)-1]=0;rejects(changed,1,"partial last record");
 need(m05_begin_ready(NULL,1,1)==-1 && m05_begin_ready((unsigned char*)positive,MAX,1)==-1,"pointer and full-cap guards");
 rejects(positive,2,"prior epoch cannot authorize epoch2");
 // Actual original five-second main loop must exhaust while procfs is already
 // empty but only real retained EAGAIN exists; no delay authorizes the probe.
 pending=base;ready=positive;append_after=0;reads=0;
 need(first_loop()==0 && reads>1,"actual main loop times out without retirement0");
 reads=0;append_after=2;need(first_loop()==1 && reads==2,"actual main loop waits for observed retirement0");
 // Add controlled epoch2 rows after the entire accepted first snapshot.
 strcpy(second_pending,positive);
 const char *at=strstr(base,"application SCHEDULE os=0 generation=1 pid=254 cpu=0");if(!at)abort();
 const char *begin=at;while(begin>base && begin[-1]!='\n')--begin;
 static char epoch2[MAX];strcpy(epoch2,begin);
 // All replacement fields are fixed-width, so this preserves exact row grammar.
 for(char*q=epoch2;(q=strstr(q,"generation=1"));q+=12)q[11]='2';
 for(char*q=epoch2;(q=strstr(q,"pid=254"));q+=7)q[6]='8';
 for(char*q=epoch2;(q=strstr(q,"tid=254"));q+=7)q[6]='8';
 for(char*q=epoch2;(q=strstr(q,"token=3 "));q+=8)q[6]='3';
 strcat(second_pending,epoch2);strcpy(second_positive,second_pending);strcat(second_positive,final2);
 need(m05_begin_ready((unsigned char*)second_pending,strlen(second_pending),2)==0,"epoch2 pending remains pending");
 need(m05_begin_ready((unsigned char*)second_positive,strlen(second_positive),2)==1,"epoch2 own real-format retirement0 required");
 pending=second_pending;ready=second_positive;append_after=0;reads=0;
 need(second_loop()==0 && reads>1,"actual second loop times out without its retirement0");
 reads=0;append_after=2;need(second_loop()==1 && reads==2,"actual second loop waits for its retirement0");
 unsigned old=reads;proc_state=0;need(begin_retired_at("/proc/mcos0",2)==0 && reads==old,"nonempty procfs blocks without probe");
 proc_state=-1;need(begin_retired_at("/proc/mcos0",2)==-1 && reads==old,"unreadable procfs is not readiness");proc_state=1;
 unsigned char bytes[MAX];int count,error;
 read_error=1;need(reboot_snapshot("/case/evidence/fixture",bytes,&count,&error)==-1,"actual reader error");read_error=0;
 full_read=1;need(reboot_snapshot("/case/evidence/fixture",bytes,&count,&error)==-1,"actual reader full cap");full_read=0;
 save_error=1;need(reboot_snapshot("/case/evidence/fixture",bytes,&count,&error)==-1,"actual evidence write failure");save_error=0;
 pending=base;ready=base;append_after=0;need(begin_retired_at("/proc/mcos0",2)==-1,"append-only snapshot rollover/regression blocks");
 printf("PASS actual Rust readiness + retained495e + exact two five-second loop bodies + original bounded reader; %u assertions; no real ioctl/probe/guest\n",checks);
 return 0;
}
