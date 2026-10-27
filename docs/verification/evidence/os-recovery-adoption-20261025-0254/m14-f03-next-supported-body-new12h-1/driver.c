/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST scalar forwarding mocks only; no actual PMU operations. */
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <stdint.h>
#include <string.h>
static struct trace { unsigned long mask; int flags; unsigned operation, calls; } seen;
static int provider_result;
static int record(unsigned operation, unsigned long mask, int flags) {
    seen.operation=operation; seen.mask=mask; seen.flags=flags; ++seen.calls;
    return provider_result;
}
int fixture_mask_provider(unsigned long mask) { return record(1,mask,0); }
int fixture_start_provider(unsigned long mask) { return record(2,mask,0); }
int fixture_stop_provider(unsigned long mask,int flags) { return record(3,mask,flags); }
/* Unchanged fallback wrappers call exactly the original provider names. */
int ihk_mc_perf_counter_mask_check(unsigned long mask) { return fixture_mask_provider(mask); }
int ihk_mc_perfctr_start(unsigned long mask) { return fixture_start_provider(mask); }
int ihk_mc_perfctr_stop(unsigned long mask,int flags) { return fixture_stop_provider(mask,flags); }
#define perf_counter_mask_check_bridge c_reference_mask
#define perf_counter_start_bridge c_reference_start
#define perf_counter_stop_bridge c_reference_stop
#include "original.C.inc"
#undef perf_counter_mask_check_bridge
#undef perf_counter_start_bridge
#undef perf_counter_stop_bridge
extern int perf_counter_mask_check_bridge(unsigned long);
extern int perf_counter_start_bridge(unsigned long);
extern int perf_counter_stop_bridge(unsigned long,int);
extern const unsigned long F03_COUNTER_CONTROL_ABI[6];
extern int (*f03_selected_mask)(unsigned long);
extern int (*f03_selected_start)(unsigned long);
extern int (*f03_selected_stop)(unsigned long,int);
static void require(int value) { if(!value) { fputs("counter-control parity failure\n",stderr); exit(1); } }
static void reset(void) { memset(&seen,0,sizeof seen); }
static void trace_oracle(unsigned operation,unsigned long mask,int flags) {
    require(seen.calls==1 && seen.operation==operation && seen.mask==mask && seen.flags==flags);
}
int main(void) {
    static const unsigned long masks[]={0,1,0x80000000UL,0x100000000UL,0x8000000000000000UL,ULONG_MAX,0x123456789abcdef0UL,0xffffffff00000000UL};
    static const int flags[]={0,1,-1,INT_MIN,INT_MAX,0x13579bdf,-22};
    static const int results[]={0,1,-1,-22,INT_MIN,INT_MAX};
    const unsigned long abi[]={sizeof(int),_Alignof(int),sizeof(unsigned long),_Alignof(unsigned long),sizeof(int(*)(unsigned long)),sizeof(int(*)(unsigned long,int))};
    unsigned pairs=0;
    require(sizeof(int)==4 && sizeof(unsigned long)==8);
    for(unsigned i=0;i<6;i++) require(F03_COUNTER_CONTROL_ABI[i]==abi[i]);
    require(f03_selected_mask==perf_counter_mask_check_bridge);
    require(f03_selected_start==perf_counter_start_bridge);
    require(f03_selected_stop==perf_counter_stop_bridge);
    for(unsigned m=0;m<8;m++) for(unsigned r=0;r<6;r++) {
        provider_result=results[r];
        reset(); require(c_reference_mask(masks[m])==results[r]); trace_oracle(1,masks[m],0);
        reset(); require(f03_selected_mask(masks[m])==results[r]); trace_oracle(1,masks[m],0); ++pairs;
        reset(); require(c_reference_start(masks[m])==results[r]); trace_oracle(2,masks[m],0);
        reset(); require(f03_selected_start(masks[m])==results[r]); trace_oracle(2,masks[m],0); ++pairs;
        for(unsigned f=0;f<7;f++) {
            reset(); require(c_reference_stop(masks[m],flags[f])==results[r]); trace_oracle(3,masks[m],flags[f]);
            reset(); require(f03_selected_stop(masks[m],flags[f])==results[r]); trace_oracle(3,masks[m],flags[f]); ++pairs;
        }
    }
    require(pairs==432);
    puts("PASS counter-control 432 C/Rust pairs; 864 exact single-call traces; ABI6; selected3");
    return 0;
}
