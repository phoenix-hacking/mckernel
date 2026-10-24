/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY: no main, command array, second queue, or hardware calls.
 * Every MMIO/IPI/warm-reset/delay boundary is a recorder; fake first-page
 * addresses are compared as scalar values, never dereferenced by this fixture.
 */
#include "ACTUAL-CPU-CONSTANTS.inc"
typedef void(*WakeupEntry)(int,unsigned long);
struct M14WakeupCase {
 unsigned long first_page;
 unsigned int ignored_read_result;
 int initial_boot_status,completion_value;
 unsigned completion_after_delay,replace_callback_slots;
};
enum { M14_WAKEUP_TAPE_WORDS=80 };
static unsigned long tape[M14_WAKEUP_TAPE_WORDS];
static unsigned failed,reads,ipis,delays;
static struct M14WakeupCase inputs;
static volatile int cpu_boot_status;
static char *first_page_va;
static void (*lapic_write)(int,unsigned int);
static unsigned int (*lapic_read)(int);
static void (*lapic_wait_icr_idle)(void);
void (*x86_issue_ipi)(unsigned int,unsigned int);
static void event(unsigned long type,unsigned long a,unsigned long b,unsigned long c){
 unsigned long n=tape[0];if(n>=19){failed=1;return;}
 unsigned long at=1+n*4;tape[at]=type;tape[at+1]=a;tape[at+2]=b;tape[at+3]=c;tape[0]=n+1;
}
static unsigned int recorded_read_second(int reg){
 event(2,(unsigned int)reg,1,inputs.ignored_read_result);reads++;
 return inputs.ignored_read_result;
}
static unsigned int recorded_read_first(int reg){
 event(2,(unsigned int)reg,0,inputs.ignored_read_result);reads++;
 if(inputs.replace_callback_slots)lapic_read=recorded_read_second;
 return inputs.ignored_read_result;
}
static void recorded_write(int reg,unsigned int value){event(1,(unsigned int)reg,value,0);}
static void recorded_wait_second(void){event(4,1,0,0);}
static void recorded_wait_first(void){
 event(4,0,0,0);if(inputs.replace_callback_slots)lapic_wait_icr_idle=recorded_wait_second;
}
static void recorded_ipi_second(unsigned int id,unsigned int low){event(3,id,low,1);ipis++;}
static void recorded_ipi_first(unsigned int id,unsigned int low){
 event(3,id,low,0);ipis++;if(inputs.replace_callback_slots)x86_issue_ipi=recorded_ipi_second;
}
void x86_set_warm_reset(unsigned long ip,char *page){event(5,ip,(unsigned long)page,0);}
void arch_delay(int us){
 event(6,(unsigned int)us,0,0);delays++;
 if(inputs.completion_after_delay==delays)cpu_boot_status=inputs.completion_value;
}
#include "ACTUAL-C-DECLARATIVE-DATA.inc"
#define __x86_wakeup original_x86_wakeup
#include "ORIGINAL-C-BODY.inc"
#undef __x86_wakeup
extern void __x86_wakeup(int,unsigned long);
static void m14_wakeup_recorded_run(WakeupEntry entry,int apicid,unsigned long ip,
 const struct M14WakeupCase *test,unsigned long output[M14_WAKEUP_TAPE_WORDS]){
 for(unsigned i=0;i<M14_WAKEUP_TAPE_WORDS;i++)tape[i]=0;
 inputs=*test;failed=reads=ipis=delays=0;
 first_page_va=(char*)inputs.first_page;cpu_boot_status=inputs.initial_boot_status;
 lapic_write=recorded_write;lapic_read=recorded_read_first;
 lapic_wait_icr_idle=recorded_wait_first;x86_issue_ipi=recorded_ipi_first;
 entry(apicid,ip);
 tape[M14_WAKEUP_TAPE_WORDS-1]=failed;
 for(unsigned i=0;i<M14_WAKEUP_TAPE_WORDS;i++)output[i]=tape[i];
}
/* Independent expected tape. Initial nonzero status still performs the first
 * SIPI iteration: only the existing post-delay volatile test controls exit.
 * Callback replacement proves reload order without inventing new concurrency.
 */
static int m14_wakeup_expected(const unsigned long got[M14_WAKEUP_TAPE_WORDS],
 int apicid,unsigned long ip,const struct M14WakeupCase *test){
 unsigned long want[M14_WAKEUP_TAPE_WORDS];for(unsigned i=0;i<M14_WAKEUP_TAPE_WORDS;i++)want[i]=0;
 unsigned n=0;unsigned long replaced=test->replace_callback_slots!=0;
#define E(k,a,b,c) do{unsigned at=1+n*4;want[at]=(k);want[at+1]=(a);want[at+2]=(b);want[at+3]=(c);n++;}while(0)
 E(5,ip,test->first_page,0);E(1,LAPIC_ESR,0,0);
 E(2,LAPIC_ESR,0,test->ignored_read_result);
 unsigned int id=(unsigned int)apicid;
 E(3,id,APIC_INT_LEVELTRIG|APIC_INT_ASSERT|APIC_DM_INIT,0);
 E(3,id,APIC_INT_LEVELTRIG|APIC_DM_INIT,replaced);E(4,0,0,0);
 int state=test->initial_boot_status;
 for(unsigned i=1;i<=3;i++){
  E(2,LAPIC_ESR,replaced,test->ignored_read_result);
  unsigned int low=(unsigned int)(ip>>12);low|=APIC_DM_STARTUP;
  E(3,id,low,replaced);E(4,replaced,0,0);E(6,200,0,0);
  if(test->completion_after_delay==i)state=test->completion_value;
  if(state!=0)break;
 }
#undef E
 want[0]=n;for(unsigned i=0;i<M14_WAKEUP_TAPE_WORDS;i++)if(got[i]!=want[i])return 1;
 return 0;
}
