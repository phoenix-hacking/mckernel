/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled callback outcomes, real selected C/Rust producer and real file IO.
 * The irreversible production PID1 pause is replaced only in the extracted
 * main control fragment, after verifying failure export happened first. */
#define ND_PAIR_LAUNCH_EXPANSION
#define ND_PAIR_LONG
#define main preserved_collector_main
#include "pair_collector.c"
#undef main
static int mode,wire_fd,held,failed;
static const char raw_trace[]="CONTROLLED_RETAINED_LINUX_TRACE no_native_acceptance=1 ownership=unknown\n";
static int wire_has(const char *needle) {
 char b[8192];ssize_t n=pread(wire_fd,b,sizeof b-1,0);if(n<0)return 0;b[n]=0;return strstr(b,needle)!=NULL;
}
static int fixture_empty(void){return 1;}
static int fixture_discover(int cpus[2]) {
 if(!wire_has("stage=callback-discover\n"))failed=1;
 cpus[0]=0;cpus[1]=1;return mode==1 || mode==2?0:-77;
}
static int fixture_launch(const int cpus[2],int *safe) {
 (void)cpus;if(!wire_has("stage=callback-launch\n"))failed=1;
 *safe=mode==1?0:1;return mode==1?-78:0;
}
static int fixture_load(void) {
 if(!wire_has("stage=callback-load\n"))failed=1;return -79;
}
static int fixture_snapshot(int action,char *out,int size) {
 if(action!=3 || !wire_has("P12_LONG_FAILURE round=0") ||
    !wire_has("ND_PAIR_LONG_ABORT\n") || !wire_has("stage=failure-trace-snapshot\n"))failed=1;
 if(mode==3)return -1;
 if(mode==5)return size;
 if(size<(int)sizeof raw_trace)return -1;
 memcpy(out,raw_trace,sizeof raw_trace-1);return sizeof raw_trace-1;
}
static void fixture_hold(void) {
 held++;if(!wire_has("P12_LONG_FAILURE round=0") || !wire_has("ownership_complete=0 rounds=0 launches=0") ||
             !wire_has("ND_PAIR_LONG_ABORT\n") || wire_has("ND_PAIR_LONG_COMPLETE ") || wire_has("ND_PAIR_PROGRESS "))failed=1;
 if(mode==3 || mode==5) {if(!wire_has("P12_LONG_FAILURE_TRACE_ERROR stage=snapshot\n"))failed=1;}
 else if(!wire_has(raw_trace) || !wire_has("P12_LONG_FAILURE_TRACE_END bytes="))failed=1;
}
#define remain_pid1() do {fixture_hold();return;} while(0)
static int actual_safe,actual_empty,actual_good;
static void actual_error_control(void) {
 int console=wire_fd,safe=1,empty=0,good=1;
#include "actual-long-error-hold-control.inc"
 actual_safe=safe;actual_empty=empty;actual_good=good;
 failed=1; /* All controlled first-round failures must retain unknown ownership. */
}
#undef remain_pid1
int main(int argc,char **argv) {
 if(argc!=2)return 90;mode=atoi(argv[1]);if(mode<0 || mode>5)return 91;
 wire_fd=open("wire",O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC,0600);if(wire_fd<0)return 92;
 if(mkdir("evidence",0700))return 93;
 if(mode==4 && save_file("evidence/long-failure.kernel.log","KEEP",4))return 94;
 long_provider.discover=fixture_discover;long_provider.launch=fixture_launch;
 long_provider.load=fixture_load;long_provider.empty=fixture_empty;long_provider.snapshot=fixture_snapshot;
 actual_safe=actual_empty=actual_good=-123;
 actual_error_control();
 if(held!=1 || failed || actual_safe!=-123 || actual_empty!=-123 || actual_good!=-123)return 95;
 if(mode==4) {
  int fd=open("evidence/long-failure.kernel.log",O_RDONLY|O_CLOEXEC);char b[5]={0};
  if(fd<0 || read(fd,b,sizeof b)!=4 || memcmp(b,"KEEP",4) || close(fd) || !wire_has("saved=0\n"))return 96;
 } else if(mode!=3 && mode!=5) {
  int fd=open("evidence/long-failure.kernel.log",O_RDONLY|O_CLOEXEC);char b[sizeof raw_trace];
  if(fd<0 || read(fd,b,sizeof b)!=(ssize_t)sizeof raw_trace-1 || memcmp(b,raw_trace,sizeof raw_trace-1) || close(fd))return 97;
 }
 if(close(wire_fd))return 98;
 printf("PASS actual_dispatch_Rust_failure_export_before_actual_hold_fragment mode=%d controlled_callbacks=1 native_acceptance=0\n",mode);
 return 0;
}
