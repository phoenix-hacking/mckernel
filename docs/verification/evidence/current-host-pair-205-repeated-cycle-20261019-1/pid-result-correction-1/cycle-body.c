#include <assert.h>
#include <stdlib.h>
#define CYCLE_MAIN_NAME cycle_pid1_never_called
#include "/home/holden/mckernel-work/host-preparation/current-host-pair-205-repeated-cycle-20261019-1/pid-result-correction-1/collector-two-complete-cycles.c"
static int scenario, helper_calls, launched_pairs, stop_calls,release_calls;
static const char *life_file,*release_file;
static void fill_pair(void) {
 const unsigned char *expected[]={cycle_expected_0,cycle_expected_1};
 const size_t sizes[]={sizeof cycle_expected_0,sizeof cycle_expected_1};
 for(int i=0;i<2;i++) {struct result *r=&pair_results[i];memset(r,0,sizeof *r);r->pid=100+i;r->clean=1;r->out.limit=r->err.limit=1024;r->out.eof=r->err.eof=1;r->out.kept=sizes[i];r->out.observed=sizes[i];r->started=100;r->out.eof_ns=r->err.eof_ns=200;r->reaped=1000;r->finished=1100;memcpy(r->out.data,expected[i],sizes[i]);}
 if(scenario==4)pair_results[0].out.data[0]='X';
}
static int fake_mkdir(const char *p,mode_t m){(void)p;assert(m==0700);return 0;}
static int fake_chdir(const char *p){assert(p && *p);return 0;}
static int fake_klogctl(int op,char *p,int size){assert(op==3 && size==262144);memcpy(p,"prior\n",6);return 6;}
static int fake_challenge(void){pair_nonce[0]=cycle_index+11;pair_nonce[1]=91;return 0;}
static int fake_discover(int cpus[2]){cpus[0]=0;cpus[1]=1;pair_generation=(cycle_index && scenario!=8)?79:41;pair_os=0;pair_host_cpus[0]=1;pair_host_cpus[1]=2;return 0;}
static int fake_run(const int cpus[2],int *safe){assert(cpus[0]==0 && cpus[1]==1);launched_pairs++;if(scenario==2){*safe=0;return -1;}return 0;}
static int fake_load(void){if(scenario==3)return -1;fill_pair();return 0;}
static int fake_retired(void){return scenario==5?-1:0;}
static int fake_prefix(const char *p,int n){(void)p;assert(n==6);return 0;}
static int fake_helper(const char *tag,const char *path,char *const av[],int *safe,struct result *r){
 (void)tag;(void)safe;assert(av && !strcmp(av[0],path));helper_calls++;memset(r,0,sizeof *r);r->clean=1;r->out.eof=r->err.eof=1;r->out.limit=r->err.limit=4096;
 r->started=10;r->reaped=20;r->finished=21;r->out.eof_ns=r->err.eof_ns=19;
 if(!strcmp(path,"/bin/native-boot"))return scenario==1?-1:0;
 const char *input;
 if(!strcmp(path,"/bin/native-lifecycle-probe")){stop_calls++;input=life_file;if(scenario==6)r->status=1;}
 else{assert(!strcmp(path,"/bin/native-resource-release-probe"));release_calls++;input=release_file;}
 FILE *f=fopen(input,"rb");assert(f);r->out.kept=fread(r->out.data,1,4096,f);assert(feof(f)&&!ferror(f)&&fclose(f)==0);r->out.observed=r->out.kept;
 return scenario==7 && release_calls ? -1:0;
}
static int fake_publish_control(int fd,const char *k,int rc,const struct result*r){(void)fd;(void)k;(void)rc;(void)r;return 0;}
static int fake_write(int fd,const void*p,size_t n){(void)fd;(void)p;(void)n;return 0;}
static int fake_emit(int fd,const char*k,const char*n,const unsigned char*p,size_t s){(void)fd;(void)k;(void)n;(void)p;(void)s;return 0;}
static int fake_publish_pair(int fd,int empty){(void)fd;assert(empty);return 0;}
#define mkdir fake_mkdir
#define chdir fake_chdir
#define klogctl fake_klogctl
#define pair_prepare_challenge fake_challenge
#define pair_discover fake_discover
#define pair_run_assigned fake_run
#define pair_load_results fake_load
#define cycle_retired fake_retired
#define cycle_log_prefix_valid fake_prefix
#define helper_capture fake_helper
#define cycle_publish_control fake_publish_control
#define write_all fake_write
#define cycle_emit_bytes fake_emit
#define publish_pair fake_publish_pair
static int fixture_run_complete_cycle(int console,int *safe,unsigned long previous_generation,const unsigned long previous_nonce[2])
{
    const char *roots[]={"/case/cycle0","/case/cycle1"};
    const char *prefixes[]={"ND_CYCLE0_PAIR","ND_CYCLE1_PAIR"};
    const char *boot_tags[]={"cycle0-boot","cycle1-boot"};
    const char *stop_tags[]={"cycle0-stop","cycle1-stop"};
    const char *release_tags[]={"cycle0-release","cycle1-release"};
    struct result boot,stop,release;
    if(cycle_index>=2 || !*safe)return -1;
    cycle_root=roots[cycle_index];cycle_pair_prefix=prefixes[cycle_index];
    if(mkdir(cycle_root,0700) || chdir(cycle_root) || mkdir("evidence",0700))return -1;
    cycle_log_before_bytes=klogctl(3,cycle_log_before,sizeof cycle_log_before);
    if(cycle_log_before_bytes<=0 || cycle_log_before_bytes==(int)sizeof cycle_log_before || pair_prepare_challenge())return -1;
    if(cycle_index && pair_nonce[0]==previous_nonce[0] && pair_nonce[1]==previous_nonce[1])return -1;
    int rc=helper_capture(boot_tags[cycle_index],"/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},safe,&boot);
    if(cycle_publish_control(console,"boot",rc,&boot) || rc || !*safe)return -1;
    memset(pair_results,0,sizeof pair_results);
    int cpus[2];
    if(pair_discover(cpus) || (cycle_index && pair_generation==previous_generation))return -1;
    if(pair_run_assigned(cpus,safe) || !*safe || pair_load_results() || cycle_pair_ok() || cycle_retired())return -1;
    int log_n=klogctl(3,cycle_log_after,sizeof cycle_log_after);
    if(cycle_log_prefix_valid(cycle_log_after,log_n))return -1;
    char line[512];int n=snprintf(line,sizeof line,"ND_CYCLE_IDENTITY {\"cycle\":%u,\"os\":%u,\"generation\":%lu,\"challenge\":\"%016lx%016lx\",\"prior_log_bytes\":%d,\"fresh_log_bytes\":%d}\n",cycle_index,pair_os,pair_generation,pair_nonce[0],pair_nonce[1],cycle_log_before_bytes,log_n-cycle_log_before_bytes);
    if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n) ||
       cycle_emit_bytes(console,"pair","assignment",(const unsigned char*)&cycle_assignment_observed,sizeof cycle_assignment_observed) ||
       cycle_emit_bytes(console,"pair","kernel_log",(const unsigned char*)cycle_log_after+cycle_log_before_bytes,(size_t)(log_n-cycle_log_before_bytes)) || publish_pair(console,1))return -1;
    rc=helper_capture(stop_tags[cycle_index],"/bin/native-lifecycle-probe",(char *const[]){"/bin/native-lifecycle-probe","0",NULL},safe,&stop);
    if(cycle_publish_control(console,"stop",rc,&stop) || !*safe || cycle_life_ok(&stop,rc))return -1;
    rc=helper_capture(release_tags[cycle_index],"/bin/native-resource-release-probe",(char *const[]){"/bin/native-resource-release-probe",NULL},safe,&release);
    if(cycle_publish_control(console,"release",rc,&release) || rc || !*safe)return -1;
    /* Public inventory is external strictconsumer's obligation; no generation/frame restoration inference. */
    return chdir("/") ? -1 : 0;
}
#undef mkdir
#undef chdir
#undef klogctl
#undef pair_prepare_challenge
#undef pair_discover
#undef pair_run_assigned
#undef pair_load_results
#undef cycle_retired
#undef cycle_log_prefix_valid
#undef helper_capture
#undef cycle_publish_control
#undef write_all
#undef cycle_emit_bytes
#undef publish_pair
int main(int argc,char **argv) {
 if(argc==2 && !strcmp(argv[1],"--pid-child")){printf("%ld\n",(long)getpid());return 0;}
 if(argc==2 && !strcmp(argv[1],"--pid-proof")) {
  struct result r;char *av[]={argv[0],"--pid-child",NULL};char *env[]={"PATH=/usr/bin:/bin",NULL};
  supervise(argv[0],av,env,NULL,2000,&r);
  assert(r.pid>0 && !r.status && !r.fault && !r.timeout && r.clean && r.out.eof && r.err.eof && !r.err.observed);
  assert(r.out.kept>0 && r.out.kept<32 && r.out.observed==r.out.kept);char text[32]={0};memcpy(text,r.out.data,r.out.kept);
  char *end=NULL;long observed=strtol(text,&end,10);assert(end && !strcmp(end,"\n") && observed==r.pid);
  puts("{\"status\":\"PASS_ACTUAL_SUPERVISOR_CHILD_PID\"}");return 0;
 }
 assert(argc==3);life_file=argv[1];release_file=argv[2];
 for(scenario=0;scenario<9;scenario++) {
  helper_calls=launched_pairs=stop_calls=release_calls=0;int safe=1;unsigned long previous=0,nonce[2]={0,0};int completed=0;
  for(cycle_index=0;cycle_index<2;cycle_index++) {int rc=fixture_run_complete_cycle(1,&safe,previous,nonce);if(rc)break;completed++;previous=pair_generation;nonce[0]=pair_nonce[0];nonce[1]=pair_nonce[1];}
  if(!scenario)assert(completed==2 && launched_pairs==2 && helper_calls==6 && stop_calls==2 && release_calls==2);
  else {assert(completed<2);if(scenario==1)assert(launched_pairs==0);if(scenario>=2 && scenario<=5)assert(stop_calls==0);if(scenario==6)assert(release_calls==0);if(scenario==7)assert(launched_pairs==1);if(scenario==8)assert(completed==1 && launched_pairs==1);}
 }
 fill_pair();assert(cycle_pair_ok()==0);pair_results[1].out.data[0]='X';assert(cycle_pair_ok()!=0);
 memcpy(cycle_log_before,"prior\n",6);cycle_log_before_bytes=6;assert(cycle_log_prefix_valid("prior\nnew\n",10)==0);assert(cycle_log_prefix_valid("wrong\nnew\n",10)!=0);assert(cycle_log_prefix_valid("prior\n",6)!=0);
 puts("{\"status\":\"PASS_ACTUAL_C_CYCLE_GATES_MODEL_ONLY\",\"positive\":1,\"refusals\":8,\"pair_byte_refusal\":true,\"prefix_vectors\":3}");assert(fflush(stdout)==0);
 fill_pair();cycle_index=0;cycle_root="/case/cycle0";cycle_pair_prefix="ND_CYCLE0_PAIR";pair_generation=41;pair_os=0;pair_host_cpus[0]=1;pair_host_cpus[1]=2;assert(publish_pair(1,1)==0);return 0;
}
