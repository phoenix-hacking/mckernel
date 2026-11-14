#define _GNU_SOURCE
#include "actual_profile.inc"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

/* Existing exact main startup statements; only resource/transport adapters
 * below are modeled. Actual handshake API/refusals have their existing test. */
static unsigned scenario, position;
static char events[8];
static const char *refusal;
static char *const payload_argv[] = {"/bin/mcexec","-t","1","0","/apps/app",NULL};
static char *const payload_env[] = {"PATH=/usr/bin:/bin","COKERNEL_PATH=/apps",NULL};
static char *const oversubscribed_boot_argv[] = {"/bin/native-boot","hidos","allow_oversubscribe",NULL};
struct result { int started; };
static int pair_prepare_challenge(void)
{ assert(position==0);events[position++]='C';return scenario==1?-1:0; }
static int helper(const char *tag,const char *path,char *const av[],int *safe)
{
 assert(position==1&&*safe==1&&!strcmp(tag,"boot")&&!strcmp(path,"/bin/native-boot"));
 assert(av==oversubscribed_boot_argv);events[position++]='B';return scenario==2?-1:0;
}
static int pair_discover(int cpus[2])
{ assert(position==2);events[position++]='A';cpus[0]=0;cpus[1]=1;return scenario==3?77:0; }
static int refuse_startup(const char *phase)
{ refusal=phase;return -1; }
static void supervise(const char *path,char *const av[],char *const env[],const char *cwd,unsigned ms,struct result *r)
{
 assert(position==3&&!strcmp(path,"/bin/mcexec")&&av==payload_argv&&env==payload_env);
 assert(!strcmp(av[4],"/apps/app")&&!strcmp(cwd,"/case/work")&&ms==10000);
 events[position++]='P';r->started=1;
}
static int run_actual_startup(void)
{
 int good=1,safe=1;struct result payload={0};
#include "actual_main_startup.inc"
finish:
 return good&&payload.started;
}
int main(void)
{
 for(scenario=0;scenario!=4;scenario++){
  position=0;events[0]=0;refusal=NULL;
  int result=run_actual_startup();events[position]=0;
  if(scenario==0)assert(result==1&&!strcmp(events,"CBAP")&&!refusal);
  if(scenario==1)assert(result==0&&!strcmp(events,"C")&&!strcmp(refusal,"challenge-prepare"));
  if(scenario==2)assert(result==0&&!strcmp(events,"CB")&&!refusal);
  if(scenario==3)assert(result==0&&!strcmp(events,"CBA")&&!strcmp(refusal,"assignment-readback"));
 }
 puts("PASS 4 actual main startup-order paths; no boots/apps");return 0;
}
