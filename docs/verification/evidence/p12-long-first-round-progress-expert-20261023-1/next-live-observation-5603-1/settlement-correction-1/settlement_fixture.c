/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual selected C strict consumer and real retained files. Application stream
 * fields are CONTROLLED from frozen oracles. Later snapshot is CONSTRUCTED by
 * appending the separately retained genuine final0 line, not a new real snapshot.
 * Controlled clock vectors test deadline edges; mode2 is a real five-second timeout. */
#define _GNU_SOURCE
#include <time.h>
static int fixture_clock(clockid_t,struct timespec *);
static int fixture_pause(const struct timespec *,struct timespec *);
#define clock_gettime fixture_clock
#define nanosleep fixture_pause
#define ND_PAIR_LAUNCH_EXPANSION
#define ND_PAIR_LONG
#define main preserved_collector_main
#include "pair_collector.c"
#undef main
#undef clock_gettime
#undef nanosleep
#include <assert.h>
static int mode,snapshots,pauses,clock_mode;
static uint64_t virtual_now=1000000000ull;
static char early[1048577],settled[1049601];
static int fixture_clock(clockid_t kind,struct timespec *out)
{
 if(!clock_mode)return clock_gettime(kind,out);
 virtual_now+=1000000ull;out->tv_sec=virtual_now/1000000000ull;out->tv_nsec=virtual_now%1000000000ull;return 0;
}
static int fixture_pause(const struct timespec *delay,struct timespec *remaining)
{pauses++;return clock_mode?0:nanosleep(delay,remaining);}
static size_t load(const char *name,char *bytes,size_t capacity)
{
 FILE *f=fopen(name,"rb");assert(f);size_t n=fread(bytes,1,capacity-1,f);
 assert(!ferror(f) && feof(f) && !fclose(f));bytes[n]=0;return n;
}
static void replace_once(char *text,const char *old,const char *value)
{
 char *at=strstr(text,old);assert(at && !strstr(at+strlen(old),old));
 size_t oldn=strlen(old),newn=strlen(value);memmove(at+newn,at+oldn,strlen(at+oldn)+1);memcpy(at,value,newn);
}
static int snapshot(int action,char *out,int capacity)
{
 assert(action==3);snapshots++;
 /* Any strict consumer call before readiness would mutate these ledgers. */
 assert(!pair_seen_pid_count && !pair_seen_token_count);
 if(mode==13)return -1;
 if(mode==14)return capacity;
 const char *data=mode==2 || mode==3 || (mode==1 && snapshots<=2)?early:settled;
 size_t n=strlen(data);assert(n<(size_t)capacity);
 memcpy(out,data,n);
 if(mode==4)virtual_now+=6000000000ull;
 if(mode==5)virtual_now=1;
 return (int)n;
}
static void controlled_results(void)
{
 pair_os=0;pair_generation=1;pair_host_cpus[0]=1;pair_host_cpus[1]=2;
 const unsigned char *bytes[]={pair_round_stdout_0,pair_round_stdout_1};
 const size_t sizes[]={sizeof pair_round_stdout_0,sizeof pair_round_stdout_1};
 for(int i=0;i<2;i++) {
  struct result *r=&pair_results[i];memset(r,0,sizeof *r);r->pid=257+i;r->clean=1;
  r->started=1;r->reaped=2;r->finished=3;r->out.eof=r->err.eof=1;r->out.eof_ns=r->err.eof_ns=3;
  memcpy(r->out.data,bytes[i],sizes[i]);r->out.kept=r->out.observed=sizes[i];
 }
}
int main(int argc,char **argv)
{
 assert(argc==2);mode=atoi(argv[1]);assert(mode>=0 && mode<=15);
 size_t n=load("../actual-failure-snapshot.normalized.log",early,sizeof early);assert(n==97303);
 memcpy(settled,early,n);size_t later=load("../actual-later-retirement.serial-record.log",settled+n,sizeof settled-n);assert(later==108);
 controlled_results();
 if(mode==0) {
  assert(pair_round_retirement_ready(early)==0);
  assert(pair_round_trace(early,257,0)==-1);pair_seen_token_count=0;
  assert(pair_round_trace(early,258,1)==0);
  printf("PASS ACTUAL_EARLY_97303B app0_strict_FAIL peer_PASS no_native_credit\n");return 0;
 }
 if(mode==6)replace_once(settled,"generation=1 pid=257 token=1016 errno=0","generation=2 pid=257 token=1016 errno=0");
 if(mode==7)replace_once(settled,"pid=257 token=1016 errno=0","pid=999 token=1016 errno=0");
 if(mode==8)replace_once(settled,"token=1016 errno=0","token=0 errno=0");
 if(mode==9)replace_once(settled,"token=1016 errno=0","token=1006 errno=0");
 if(mode==10)replace_once(settled,"os=0 generation=1 pid=257 token=1016","os=1 generation=1 pid=257 token=1016");
 if(mode==11)replace_once(settled,"application cleanup ACK os=0 generation=1 pid=257 ","CONTROLLED missing ACK os=0 generation=1 pid=257 ");
 if(mode==12)pair_results[1].pid=257;
 if(mode==15)strcat(settled,"application retirement os=0 generation=1 pid=257 token=1017 errno=-11\n");
 if(mode==4 || mode==5 || mode==7)clock_mode=1;
 if(mkdir("evidence",0700) || mkdir("evidence/round0",0700))return 90;
 strcpy(pair_evidence_dir,"./evidence/round0");pair_active_round=0;
 long_provider.snapshot=snapshot;
 uint64_t before=now_ns();uint64_t outer=before+(mode==3?80000000ull:20000000000ull);
 if(mode==1)assert(pair_round_retirement_ready(settled)==1);
 /* Exactly one strict-gate invocation. Its readiness loop never retries it. */
 int code=pair_round_gate(outer);uint64_t after=now_ns();
 if(mode==1) {
  assert(code==0 && snapshots==3 && pauses==2 && pair_seen_pid_count==2 && pair_seen_token_count==4);
  assert(save_file("CONSTRUCTED-SETTLED.log",settled,strlen(settled))==0);
  printf("PASS CONSTRUCTED_APPEND genuine_later_final0 readiness_two_pending_polls strict_gate_ONCE snapshots=%d\n",snapshots);
 } else {
  assert(code==-1);
  if(mode==11)assert(pair_seen_pid_count==2 && !strcmp(pair_fail_phase,"app0_trace_oracle"));
  else assert(!pair_seen_pid_count && !pair_seen_token_count);
  if(mode==2)assert(after-before>=5000000000ull && after-before<6000000000ull && snapshots>=2);
  if(mode==3)assert(after-before>=80000000ull && after-before<1000000000ull && snapshots>=2);
  printf("PASS CONTROLLED_NEGATIVE mode=%d snapshots=%d pauses=%d elapsed_ns=%llu phase=%s ledgers_unchanged_before_strict=%d\n",mode,snapshots,pauses,(unsigned long long)(after-before),pair_fail_phase,mode!=11);
 }
 return 0;
}
