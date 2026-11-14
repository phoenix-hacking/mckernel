/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact selected-source frame function; inert HOST fixtures only. */
#ifndef ND_FUTEX
#error "exact original FP4096 profile required"
#endif
#define main collector_runtime_main_unused
#include "/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native199-helper-failure-export-1/errno-correction-1/native_diagnostic_guest_collector.helper-diagnostic.c"
#undef main
_Static_assert(STREAM_LIMIT == 4096u, "original FP cap");
_Static_assert(FRAME_LIMIT == 8192u, "original large frame");
static const unsigned char oracle[] = "FPTHREAD v1 threads=2 same_permitted_cpu=1 distinct_tid=1\nthread0 rounds=64 ymm_lanes=64 peer_progress=64 yield_min=64 controls=077f/3f80 restored=1\nthread1 rounds=64 ymm_lanes=64 peer_progress=64 yield_min=64 controls=0b7f/5f80 restored=1\nFPTHREAD PASS\n";
static void setup(struct result *r) {
    memset(r,0,sizeof *r);r->clean=1;r->started=1;r->reaped=2;r->finished=3;
    r->out.eof=r->err.eof=1;r->out.eof_ns=r->err.eof_ns=2;
}
int main(void) {
    struct result r;char buffer[FRAME_LIMIT];int n;
    setup(&r);r.out.kept=r.out.observed=sizeof oracle-1;memcpy(r.out.data,oracle,sizeof oracle-1);
    n=frame(buffer,&r,1);if(n<=0 || n>=(int)FRAME_LIMIT)return 1;
    char *first=strstr(buffer,"\"limit\":4096");if(!first || !strstr(first+1,"\"limit\":4096"))return 2;
    if(fwrite(buffer,1,(size_t)n,stdout)!=(size_t)n)return 3;
    setup(&r);r.out.kept=r.out.observed=1025;memset(r.out.data,'Q',1025);
    n=frame(buffer,&r,1);if(n<=0 || !strstr(buffer,"\"observed\":1025,\"retained\":1025") || strstr(buffer,"\"truncated\":true"))return 4;
    setup(&r);r.out.kept=r.out.observed=STREAM_LIMIT;memset(r.out.data,'Q',STREAM_LIMIT);
    if(frame(buffer,&r,1)>=0)return 5; /* oversized JSON frame must fail */
    setup(&r);r.out.kept=16;r.out.observed=17;memset(r.out.data,'Q',16);
    n=frame(buffer,&r,1);if(n<=0 || !strstr(buffer,"\"truncated\":true"))return 6;
    puts("FP4096_FRAME_CHECKS PASS");return 0;
}
