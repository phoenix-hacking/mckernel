#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#define STREAM_LIMIT 1024u
#define FRAME_LIMIT 4096u
#define BOOT_TIMEOUT_MS 60000u
#define HELPER_TIMEOUT_MS 10000u
struct stream {
    unsigned char data[STREAM_LIMIT];
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
    struct stream out, err;
    int status, fault, timeout, clean;
    int child_stage, child_errno;
    uint64_t started, reaped, finished;
};
/* Preserve only the first actual pre-payload helper refusal. */
static struct {
    const char *tag;
    struct result actual;
    int evidence_fault, ready;
} failed_helper;
static char *const helper_env[] = {"PATH=/bin:/sbin:/usr/bin:/usr/sbin", "LC_ALL=C", NULL};

static struct result modeled;
static int save_bad;
static char console_bytes[FRAME_LIMIT+1];
static size_t console_size;
static void supervise(const char *p, char *const a[], char *const e[],const char *c,unsigned t,struct result *r)
{ (void)p;(void)a;(void)e;(void)c;(void)t;*r=modeled; }
static int save_file(const char *p,const void *b,size_t n)
{ (void)p;(void)b;(void)n;if(save_bad){errno=EIO;return -1;}return 0; }
static ssize_t fixture_write(int fd,const void *b,size_t n)
{ assert(fd==42);assert(n<=FRAME_LIMIT);memcpy(console_bytes,b,n);console_size=n;console_bytes[n]=0;return (ssize_t)n; }
#define write fixture_write
#include "actual_helper_export_bodies.inc"
#undef write
static void reset(void)
{ memset(&failed_helper,0,sizeof failed_helper);memset(&modeled,0,sizeof modeled);console_size=0;save_bad=0;modeled.clean=1;modeled.status=256;modeled.started=11;modeled.reaped=22;modeled.finished=33;modeled.out.eof=modeled.err.eof=1; }
static void dump(const char *dir,const char *name)
{ char path[4096];int n=snprintf(path,sizeof path,"%s/%s",dir,name);assert(n>0&&(size_t)n<sizeof path);FILE *f=fopen(path,"wbx");assert(f);assert(fwrite(console_bytes,1,console_size,f)==console_size);assert(fclose(f)==0); }
int main(int argc,char **argv)
{
 assert(argc==2);int safe;struct result payload;
 /* Modeled helper bytes are explicitly NOT recovered historical helper data. */
 reset();safe=1;memcpy(modeled.err.data,"modeled failure\n",16);modeled.err.kept=modeled.err.observed=16;
 assert(helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe)==-1&&safe);
 modeled.status=512;assert(helper("load-mcctrl","/sbin/insmod",(char *const[]){"insmod",NULL},&safe)==-1);
 assert(!strcmp(failed_helper.tag,"boot")&&failed_helper.actual.status==256);
 assert(publish_diagnostic(42,NULL,0,safe)==0);assert(strstr(console_bytes,"ND_HELPER_FAIL ")==console_bytes);dump(argv[1],"missing-main.frame");
 reset();safe=1;modeled.status=0;save_bad=1;assert(helper("load-mcctrl","/sbin/insmod",(char *const[]){"insmod",NULL},&safe)==-1&&safe);
 memset(&payload,0,sizeof payload);payload.status=-1;payload.finished=9129620174ull;
 assert(publish_diagnostic(42,&payload,0,safe)==0);dump(argv[1],"empty-main.frame");
 reset();safe=1;modeled.status=0;assert(helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe)==0);assert(!failed_helper.ready);
 payload=modeled;payload.started=11;assert(publish_diagnostic(42,&payload,1,safe)==0);assert(strstr(console_bytes,"ND_PAYLOAD ")==console_bytes);assert(!strstr(console_bytes,"ND_HELPER_FAIL"));dump(argv[1],"success.frame");
 reset();safe=1;modeled.out.kept=modeled.out.observed=STREAM_LIMIT+1;assert(helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe)==-1);assert(publish_diagnostic(42,NULL,0,safe)==-1&&console_size==0);
 reset();safe=1;memset(modeled.out.data,'a',STREAM_LIMIT);memset(modeled.err.data,'b',STREAM_LIMIT);modeled.out.kept=modeled.out.observed=modeled.err.kept=modeled.err.observed=STREAM_LIMIT;assert(helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe)==-1);assert(publish_diagnostic(42,NULL,0,safe)==0);assert(console_size<=FRAME_LIMIT);dump(argv[1],"frame-cap-omission.frame");
 reset();safe=1;modeled.clean=0;assert(helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe)==-1&&!safe);assert(publish_diagnostic(42,NULL,0,safe)==-1&&console_size==0);dump(argv[1],"unsafe.frame");
 puts("PASS five actual helper/export body cases; modeled helper bytes, historical helper remains unknown");return 0;
}
