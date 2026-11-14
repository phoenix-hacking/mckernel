/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact selected collector/strict gate. All CPU/module/provider operations are
 * excluded; snapshot/time fields are CONTROLLED. The full 1MiB suffix combines
 * separately retained genuine records with CONSTRUCTED unrelated whole-record
 * padding. It is not the unexported round90 snapshot or native acceptance.
 */
#define _GNU_SOURCE
#include <time.h>
#include <sys/klog.h>
#include <assert.h>
#include <errno.h>
static int fixture_clock(clockid_t,struct timespec *);
static int fixture_pause(const struct timespec *,struct timespec *);
static int forbidden_klogctl(int action,char *buf,int size){(void)action;(void)buf;(void)size;assert(!"unexpected real klog path");return -1;}
#define clock_gettime fixture_clock
#define nanosleep fixture_pause
#define klogctl forbidden_klogctl
#define ND_PAIR_LAUNCH_EXPANSION
#define ND_PAIR_LONG
#define main preserved_collector_main
#if CAPACITY_FIX
#include "candidate/pair_collector.c"
#else
#include "preimage/pair_collector.c"
#endif
#undef main
#undef clock_gettime
#undef nanosleep
#undef klogctl
#define LIMIT 1048576u
static char records[1049601],payload[LIMIT+1];
static int mode,snapshots,pauses,clock_mode,strict_invocations;
static uint64_t virtual_now=1000000000ull;
static int fixture_clock(clockid_t which,struct timespec *out)
{
 if(!clock_mode)return clock_gettime(which,out);
 virtual_now+=MS;out->tv_sec=virtual_now/1000000000ull;out->tv_nsec=virtual_now%1000000000ull;return 0;
}
static int fixture_pause(const struct timespec *delay,struct timespec *remaining)
{pauses++;return clock_mode?0:nanosleep(delay,remaining);}
static size_t load(const char *root,const char *name,char *out,size_t capacity)
{
 char path[PATH_MAX];int z=snprintf(path,sizeof path,"%s/%s",root,name);assert(z>0&&(size_t)z<sizeof path);
 FILE *f=fopen(path,"rb");assert(f);size_t n=fread(out,1,capacity-1,f);assert(!ferror(f)&&feof(f)&&!fclose(f));out[n]=0;return n;
}
static void replace_once(char *text,const char *old,const char *value)
{
 char *p=strstr(text,old);assert(p&&!strstr(p+strlen(old),old));size_t a=strlen(old),b=strlen(value);assert(strlen(text)+b-a<sizeof records);memmove(p+b,p+a,strlen(p+a)+1);memcpy(p,value,b);
}
static void pad_whole_records(void)
{
 size_t n=strlen(records);assert(n<LIMIT&&n&&records[n-1]=='\n');memcpy(payload,records,n);
 while(n<LIMIT){size_t left=LIMIT-n,span=left>256?128:left;assert(span>=sizeof("<6>[  123.000000] CONSTRUCTED_CAPACITY_PADDING "));
  const char prefix[]="<6>[  123.000000] CONSTRUCTED_CAPACITY_PADDING ";memcpy(payload+n,prefix,sizeof prefix-1);memset(payload+n+sizeof prefix-1,'p',span-(sizeof prefix-1));payload[n+span-1]='\n';n+=span;}
 payload[LIMIT]=0;assert(strlen(payload)==LIMIT&&payload[LIMIT-1]=='\n');
}
static int snapshot(int action,char *out,int capacity)
{
 assert(action==3&&capacity==(int)LIMIT);snapshots++;
 assert(!pair_seen_pid_count&&!pair_seen_token_count);
 if(mode==1){errno=EACCES;return -1;}
 if(mode==2){errno=ENOSYS;return 0;}
 if(mode==3){errno=0;return capacity+1;}
 memcpy(out,payload,LIMIT);errno=EEXIST;
 if(mode==11)virtual_now+=6000000000ull;
 return capacity;
}
static void results(void)
{
 pair_os=0;pair_generation=1;pair_host_cpus[0]=1;pair_host_cpus[1]=2;
 const unsigned char *bytes[]={pair_round_stdout_0,pair_round_stdout_1};const size_t sizes[]={sizeof pair_round_stdout_0,sizeof pair_round_stdout_1};
 for(int i=0;i<2;i++){struct result *r=&pair_results[i];memset(r,0,sizeof *r);r->pid=257+i;r->clean=1;r->started=1;r->reaped=2;r->finished=3;r->out.eof=r->err.eof=1;r->out.eof_ns=r->err.eof_ns=3;memcpy(r->out.data,bytes[i],sizes[i]);r->out.kept=r->out.observed=sizes[i];}
}
static int expected_console(const char *path)
{
 FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&n<(long)LIMIT+4096);rewind(f);char *b=malloc((size_t)n+1);assert(b);assert(fread(b,1,(size_t)n,f)==(size_t)n&&!fclose(f));b[n]=0;
 int okay=strstr(b,"ND_PAIR_LONG_ABORT\n")&&strstr(b,"P12_LONG_FAILURE_TRACE_BEGIN bytes=1048576 saved=1\n")&&strstr(b,"P12_LONG_FAILURE_TRACE_END bytes=1048576\n");free(b);return okay;
}
int main(int argc,char **argv)
{
 assert(argc==3);mode=atoi(argv[1]);assert((mode>=0&&mode<=16)||(mode>=20&&mode<=23));
 size_t n=load(argv[2],"actual-failure-snapshot.normalized.log",records,sizeof records);assert(n==97303);
 size_t later=load(argv[2],"actual-later-retirement.serial-record.log",records+n,sizeof records-n);assert(later==108);
 results();
 if(mode==4)replace_once(records,"generation=1 pid=257 token=1016 errno=0","generation=2 pid=257 token=1016 errno=0");
 if(mode==5)replace_once(records,"pid=257 token=1016 errno=0","pid=999 token=1016 errno=0");
 if(mode==6)replace_once(records,"token=1016 errno=0","token=0 errno=0");
 if(mode==7)replace_once(records,"token=1016 errno=0","token=1006 errno=0");
 if(mode==8)replace_once(records,"application cleanup ACK os=0 generation=1 pid=257 ","CONSTRUCTED missing ACK os=0 generation=1 pid=257 ");
 if(mode==9)replace_once(records,"application SCHEDULE os=0 generation=1 pid=257 ","CONSTRUCTED missing SCHEDULE os=0 generation=1 pid=257 ");
 if(mode==10||mode==12)records[n]=0; /* remove separately retained current final0 */
 if(mode==13)pair_results[1].pid=257;
 if(mode==14)strcat(records,"application retirement os=0 generation=1 pid=257 token=1017 errno=-11\n");
 if(mode==15)replace_once(records,"token=1016 errno=0","token=1016 errno=malformed");
 pad_whole_records();
 if(mode==16)payload[LIMIT-1]='x';
 assert(!mkdir("evidence",0700)&&!mkdir("evidence/round0",0700));strcpy(pair_evidence_dir,"./evidence/round0");pair_active_round=0;long_provider.snapshot=snapshot;
 if(mode>=20){
  int original_mode=mode;mode=mode==21?1:mode==22?3:mode==23?2:0;
  FILE *console=fopen("failure-export.console","w+b");assert(console);long_observed_phase="callback-gate";long_observed_result=-5;long_observed_summary.ownership_complete=1;
  int code=long_failure_export(fileno(console),1);assert(!fflush(console)&&!fclose(console));
#if CAPACITY_FIX
  if(original_mode==20){struct stat st;assert(code==0&&!stat("evidence/long-failure.kernel.log",&st)&&st.st_size==LIMIT&&expected_console("failure-export.console"));}
  else assert(code==-1);
#else
  assert(code==-1);
#endif
  assert(!pair_seen_pid_count&&!pair_seen_token_count);
  printf("PASS FAILURE_EXPORT mode=%d candidate=%d snapshots=%d raw_trace_acceptance=0\n",original_mode,CAPACITY_FIX,snapshots);return 0;
 }
 if(mode==5||mode==11)clock_mode=1;
 uint64_t before=now_ns(),outer=before+(mode==12?80000000ull:20000000000ull);
 strict_invocations++;int code=pair_round_gate(outer);uint64_t after=now_ns();assert(strict_invocations==1);
#if CAPACITY_FIX
 if(mode==0){assert(code==0&&snapshots==1&&!pauses&&pair_seen_pid_count==2&&pair_seen_token_count==4&&!pair_settlement_snapshot_error.valid);assert(!save_file("CONSTRUCTED-FULL-VALID-SUFFIX.log",payload,LIMIT));printf("PASS CONSTRUCTED_FULL_VALID_SUFFIX bytes=%u strict_gate_ONCE exact_current_pid_generation_token_final0=1 no_native_credit\n",LIMIT);}
 else{
  assert(code==-1);
  if(mode==10)assert(after-before>=5000000000ull&&after-before<6000000000ull&&snapshots>1&&!pair_seen_pid_count&&!pair_seen_token_count);
  if(mode==12)assert(after-before>=80000000ull&&after-before<1000000000ull&&snapshots>1&&!pair_seen_pid_count&&!pair_seen_token_count);
  if(mode==8||mode==9)assert(pair_seen_pid_count==2);
  printf("PASS CONTROLLED_NEGATIVE mode=%d snapshots=%d strict_gate_ONCE elapsed_ns=%llu phase=%s\n",mode,snapshots,(unsigned long long)(after-before),pair_fail_phase);
 }
#else
 assert(mode==0&&code==-1&&snapshots==1&&!pair_seen_pid_count&&!pair_seen_token_count&&pair_settlement_snapshot_error.valid&&pair_settlement_snapshot_error.n==(int)LIMIT);
 printf("PASS ORIGINAL_FULL_COUNT_GUARD_FAIL bytes=%u no_actual_round90_data\n",LIMIT);
#endif
 return 0;
}
