/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Explicit PMU/atomic provider mocks: record bits once, never dereference pointers. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include <stddef.h>
struct mc_perf_event;
typedef struct { long counter64; } ihk_atomic64_t;
static struct trace { uintptr_t pointer; int counter, mode; unsigned int code; unsigned operation, calls; } seen;
static int int_result;
static long long_result;
int fixture_extra_provider(struct mc_perf_event *event) { ++seen.calls;seen.operation=1;seen.pointer=(uintptr_t)event;return int_result; }
int fixture_init_provider(int counter,unsigned int code,int mode) { ++seen.calls;seen.operation=2;seen.counter=counter;seen.code=code;seen.mode=mode;return int_result; }
long fixture_atomic_provider(const ihk_atomic64_t *value) { ++seen.calls;seen.operation=3;seen.pointer=(uintptr_t)value;return long_result; }
int ihk_mc_perfctr_set_extra(struct mc_perf_event *event) { return fixture_extra_provider(event); }
int ihk_mc_perfctr_init_raw(int counter,unsigned int code,int mode) { return fixture_init_provider(counter,code,mode); }
long ihk_atomic64_read(const ihk_atomic64_t *value) { return fixture_atomic_provider(value); }
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_perfctr_init_raw),int (*)(int,unsigned int,int)),"genuine supported x86 u32-code provider ABI");
_Static_assert(sizeof(ihk_atomic64_t)==8 && _Alignof(ihk_atomic64_t)==8 && offsetof(ihk_atomic64_t,counter64)==0,"original atomic64 data ABI");
#define perf_counter_extra_set_bridge original_extra
#define perf_counter_init_raw_bridge original_init
#define perf_event_atomic64_read_bridge original_atomic
#include "original.C.inc"
#undef perf_counter_extra_set_bridge
#undef perf_counter_init_raw_bridge
#undef perf_event_atomic64_read_bridge
extern int perf_counter_extra_set_bridge(void *);
extern int perf_counter_init_raw_bridge(int,unsigned long,int);
extern long syscall_atomic64_read_bridge(void *);
extern int (*f03_selected_extra)(void *);
extern int (*f03_selected_init)(int,unsigned long,int);
extern long (*f03_selected_atomic)(void *);
extern const unsigned long F03_NEXT3_ABI[16];
static void require(int ok) { if(!ok) { fputs("perf-next3 parity failure\n",stderr);exit(1); } }
static void reset(void) { seen.pointer=0;seen.counter=0;seen.mode=0;seen.code=0;seen.operation=0;seen.calls=0; }
static void pointer_oracle(uintptr_t pointer,unsigned operation) { require(seen.calls==1 && seen.pointer==pointer && seen.operation==operation); }
static void init_oracle(int counter,unsigned int code,int mode) { require(seen.calls==1 && seen.operation==2 && seen.counter==counter && seen.code==code && seen.mode==mode); }
int main(void) {
    static const uintptr_t pointers[]={0,1,8,0x12345000UL,0x8000000000000000UL,ULONG_MAX,0x7fffffffffffffffUL,0x0000ffff00000000UL};
    static const int counters[]={0,-1,INT_MIN,INT_MAX};
    static const unsigned long configs[]={0,1,0x7fffffffUL,0x80000000UL,0xffffffffUL,0x100000000UL,0x8000000000000000UL,ULONG_MAX};
    static const int modes[]={0,-1,INT_MIN,INT_MAX};
    static const int results[]={0,1,-1,-22,INT_MIN,INT_MAX};
    static const long reads[]={0,1,-1,-14,LONG_MIN,LONG_MAX,0x123456789abcdefL};
    const unsigned long abi[]={sizeof(int),_Alignof(int),sizeof(unsigned long),_Alignof(unsigned long),sizeof(long),_Alignof(long),sizeof(unsigned int),_Alignof(unsigned int),sizeof(void *),_Alignof(void *),sizeof(int(*)(void *)),sizeof(int(*)(int,unsigned long,int)),sizeof(long(*)(void *)),sizeof(ihk_atomic64_t),_Alignof(ihk_atomic64_t),offsetof(ihk_atomic64_t,counter64)};
    unsigned extra=0,init=0,atomic=0;
    require(sizeof(int)==4 && sizeof(unsigned int)==4 && sizeof(long)==8 && sizeof(unsigned long)==8 && sizeof(void*)==8);
    for(unsigned i=0;i<16;i++)require(F03_NEXT3_ABI[i]==abi[i]);
    require(f03_selected_extra==perf_counter_extra_set_bridge && f03_selected_init==perf_counter_init_raw_bridge && f03_selected_atomic==syscall_atomic64_read_bridge);
    for(unsigned p=0;p<8;p++) {
        for(unsigned r=0;r<6;r++) {
            int_result=results[r];reset();require(original_extra((void*)pointers[p])==results[r]);pointer_oracle(pointers[p],1);
            reset();require(f03_selected_extra((void*)pointers[p])==results[r]);pointer_oracle(pointers[p],1);++extra;
        }
        for(unsigned r=0;r<7;r++) {
            long_result=reads[r];reset();require(original_atomic((void*)pointers[p])==reads[r]);pointer_oracle(pointers[p],3);
            reset();require(f03_selected_atomic((void*)pointers[p])==reads[r]);pointer_oracle(pointers[p],3);++atomic;
        }
    }
    for(unsigned c=0;c<4;c++)for(unsigned h=0;h<8;h++)for(unsigned m=0;m<4;m++)for(unsigned r=0;r<6;r++) {
        int_result=results[r];reset();require(original_init(counters[c],configs[h],modes[m])==results[r]);init_oracle(counters[c],(unsigned int)configs[h],modes[m]);
        reset();require(f03_selected_init(counters[c],configs[h],modes[m])==results[r]);init_oracle(counters[c],(unsigned int)configs[h],modes[m]);++init;
    }
    require(extra==48 && init==768 && atomic==56 && extra+init+atomic==872);
    puts("PASS perf-next3 872 C/Rust pairs; 1744 exact provider traces; ABI16; selected3; reused atomic bridge");
    return 0;
}
