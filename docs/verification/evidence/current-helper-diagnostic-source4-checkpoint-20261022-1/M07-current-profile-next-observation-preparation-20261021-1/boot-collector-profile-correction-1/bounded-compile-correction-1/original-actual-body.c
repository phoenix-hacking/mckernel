#define main collector_main_never_called
#include "/home/holden/mckernel-work/scratch/native-core-current942-preparation-20261017-1/threads-1/collector-threads.c"
#undef main
int main(void) {
 struct result r={0};r.status=7<<8;r.clean=r.out.eof=r.err.eof=1;r.started=1;r.reaped=2;r.finished=3;r.child_stage=4;r.child_errno=22;
 memset(r.out.data,'A',STREAM_LIMIT);r.out.kept=r.out.observed=STREAM_LIMIT;r.out.eof_ns=2;
 memset(r.err.data,'B',STREAM_LIMIT);r.err.kept=r.err.observed=STREAM_LIMIT;r.err.eof_ns=2;
#ifdef CORRECTED
 first_failed_helper=r;first_failed_helper_tag="boot";if(publish_helper_failure(STDOUT_FILENO))return 9;
#endif
 struct result payload={0};payload.status=-1;payload.finished=4;
 return publish(STDOUT_FILENO,&payload,0)?10:0;
}
