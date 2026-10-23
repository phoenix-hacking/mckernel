/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual original C entry/fallback and actual Rust entry/body; only HOST CPU/MSR
 * primitives are modeled. No privileged instruction, target CPU or native claim.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#include "actual_msr_constants.h"
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(uint64_t)==8,"x86_64 LP64 ABI");
int no_turbo;
static int kvm;
static unsigned long eax_value,ecx_value,platform_value,ratio_value;
struct event { unsigned long kind,index,value; };
static struct event events[8];static unsigned count;
static void record(unsigned long k,unsigned long i,unsigned long v){ if(count>=8){__builtin_trap();} events[count++]=(struct event){k,i,v}; }
int running_on_kvm(void){record(1,0,(unsigned long)(long)kvm);return kvm;}
int x86_running_on_kvm_bridge(void){return running_on_kvm();}
void x86_cpuid6_bridge(unsigned long *a,unsigned long *c){record(2,eax_value,ecx_value);*a=eax_value;*c=ecx_value;}
unsigned long rdmsr(int reg){record(3,(unsigned)reg,0);return reg==MSR_PLATFORM_INFO?platform_value:ratio_value;}
void wrmsr(int reg,unsigned long value){record(4,(unsigned)reg,value);}
unsigned long x86_read_msr_bridge(int reg){return rdmsr(reg);}
void x86_write_msr_bridge(int reg,unsigned long value){wrmsr(reg,value);}
extern void init_pstate_and_turbo(void);
extern int x86_init_pstate_turbo_body_result(int,int,int,int,int,int(*)(void),void(*)(unsigned long*,unsigned long*),unsigned long(*)(int),void(*)(int,unsigned long));
#include "original_selected.inc"
#include "original_fallback_modeled_cpuid.inc"
#define CHECK(c) do {if(!(c)){fprintf(stderr,"FAIL line=%d cases=%lu\n",__LINE__,cases);return 1;}} while(0)
int main(void){
 unsigned long cases=0;int kv[]={0,1,-1},turbo[]={0,1,-1,INT_MIN};
 unsigned long ax[]={0,2,1,~0UL},platform[]={0,~0UL,0xff00,0x123456789abcdef0UL,1UL<<63,0xdeadbeef};
 unsigned long ratio[]={0,~0UL,0x123456789abcdef0UL,0x7f};
 struct event expected[8];unsigned expected_count;
 for(unsigned k=0;k<3;k++)for(unsigned e=0;e<16;e++)for(unsigned a=0;a<4;a++)for(unsigned t=0;t<4;t++)for(unsigned p=0;p<6;p++)for(unsigned q=0;q<4;q++){
 kvm=kv[k];ecx_value=e;eax_value=ax[a];no_turbo=turbo[t];platform_value=platform[p];ratio_value=ratio[q];
 memset(events,0,sizeof(events));count=0;original_selected_init_pstate_and_turbo();expected_count=count;memcpy(expected,events,sizeof(events));
 memset(events,0,sizeof(events));count=0;init_pstate_and_turbo();CHECK(count==expected_count&&memcmp(events,expected,sizeof(events))==0);
 memset(events,0,sizeof(events));count=0;original_fallback_init_pstate_and_turbo();CHECK(count==expected_count&&memcmp(events,expected,sizeof(events))==0);
 ++cases;
 }
 CHECK(cases==18432);
 for(unsigned mask=0;mask<15;mask++){
 count=0;int result=x86_init_pstate_turbo_body_result(no_turbo,MSR_PLATFORM_INFO,MSR_NHM_TURBO_RATIO_LIMIT,MSR_IA32_PERF_CTL,MSR_IA32_ENERGY_PERF_BIAS,(mask&1)?x86_running_on_kvm_bridge:0,(mask&2)?x86_cpuid6_bridge:0,(mask&4)?x86_read_msr_bridge:0,(mask&8)?x86_write_msr_bridge:0);
 CHECK(result==-22&&count==0);
 }
 printf("PASS actual_selected_C_Rust_entry_pairs=%lu original_fallback_Rust_pairs=%lu missing_callback_masks=15 ordered_primitive_calls=1 FULL_VOID_SIGNATURE_HOST_CPU_MSR_MODELED_NO_NATIVE\n",cases,cases);return 0;
}
