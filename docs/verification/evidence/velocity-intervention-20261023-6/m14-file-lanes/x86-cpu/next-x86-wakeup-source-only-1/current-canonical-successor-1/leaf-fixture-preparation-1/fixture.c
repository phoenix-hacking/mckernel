/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled provider transport only; no warm-reset/MMIO/IPI/delay instruction.
 */
extern int printf(const char*,...);
#include "FUTURE-RECORDED-BOUNDARIES.c.inc"
#include "FUTURE-C-TYPE-ABI.c.inc"
extern const unsigned long M14_RUST_WAKEUP_TYPE_ABI[22];
int main(void){
 unsigned failures=0;unsigned long pairs=0;
 for(unsigned i=0;i<22;i++)if(M14_C_WAKEUP_TYPE_ABI[i]!=M14_RUST_WAKEUP_TYPE_ABI[i])failures++;
 int ids[5]={(-0x7fffffff-1),-1,0,1,0x7fffffff};
 unsigned long ips[5]={0,1,0xfff,0x1000,~0UL};
 unsigned long pages[4]={0,1,1UL<<63,~0UL};
 unsigned int read_results[2]={0,~0U};
 int states[3]={0,1,-1};
 for(unsigned a=0;a<5;a++)for(unsigned b=0;b<5;b++)for(unsigned p=0;p<4;p++)
 for(unsigned r=0;r<2;r++)for(unsigned initial=0;initial<3;initial++)
 for(unsigned complete=0;complete<5;complete++)for(unsigned result=0;result<3;result++)
 for(unsigned replace=0;replace<2;replace++){
  struct M14WakeupCase test={.first_page=pages[p],.ignored_read_result=read_results[r],
   .initial_boot_status=states[initial],.completion_value=states[result],
   .completion_after_delay=complete,.replace_callback_slots=replace};
  unsigned long c[M14_WAKEUP_TAPE_WORDS],rust[M14_WAKEUP_TAPE_WORDS];
  m14_wakeup_recorded_run(original_x86_wakeup,ids[a],ips[b],&test,c);
  m14_wakeup_recorded_run(__x86_wakeup,ids[a],ips[b],&test,rust);
  if(m14_wakeup_expected(c,ids[a],ips[b],&test)||m14_wakeup_expected(rust,ids[a],ips[b],&test))failures++;
  for(unsigned i=0;i<M14_WAKEUP_TAPE_WORDS;i++)if(c[i]!=rust[i]){failures++;break;}
  pairs++;
 }
 printf("M14 wakeup C/Rust: pairs=%lu ABI=22 failures=%u\n",pairs,failures);
 printf("NOTEXECUTED: warmReset MMIO IPI delayISA APstartup NULLfreeze native\n");
 return failures?1:0;
}
