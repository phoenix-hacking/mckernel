/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY, no main/driver/argv/ready queue.
 * Future harness includes the unchanged actual signal/context tape boundaries
 * used by the int3 fragment, selecting the exact debug format and DR6 event.
 * This independent finite table covers ignored bits and BS-over-breakpoint
 * priority; raw HardwareDebugRegisterReader/debug_handler are never executed.
 */
#include <ihk/context.h>
#include <registers.h>
#include <signal.h>
struct M14DebugStateVector{unsigned long dr6,saved_flags,expected_flags;int expected_code;};
static const struct M14DebugStateVector M14_DEBUG_STATES[]={
 {0,~0UL,~0UL,0},
 {DB6_BD,~0UL,~0UL,0},{DB6_BT,~0UL,~0UL,0},{1UL<<63,~0UL,~0UL,0},
 {DB6_B0,~0UL,~0UL,TRAP_HWBKPT},{DB6_B1,~0UL,~0UL,TRAP_HWBKPT},
 {DB6_B2,~0UL,~0UL,TRAP_HWBKPT},{DB6_B3,~0UL,~0UL,TRAP_HWBKPT},
 {DB6_B0|DB6_B1|DB6_B2|DB6_B3,~0UL,~0UL,TRAP_HWBKPT},
 {DB6_BS,~0UL,~(unsigned long)RFLAGS_TF,TRAP_TRACE},
 {DB6_BS|DB6_B0,~0UL,~(unsigned long)RFLAGS_TF,TRAP_TRACE},
 {~0UL,~0UL,~(unsigned long)RFLAGS_TF,TRAP_TRACE},
 {DB6_BS,0,0,TRAP_TRACE},
 {DB6_BS,0x8000000000000100UL,0x8000000000000000UL,TRAP_TRACE},
};
struct M14ControlledDr6 {
 struct x86_user_context*active;
 const struct M14DebugStateVector*vector;
 unsigned calls,failed;
 unsigned long observed_before_read;
};
static struct M14ControlledDr6 m14_dr6;
void m14_debug_begin_dr6(struct x86_user_context*active,const struct M14DebugStateVector*vector){
 m14_dr6.active=active;m14_dr6.vector=vector;m14_dr6.calls=0;m14_dr6.failed=0;
 m14_dr6.observed_before_read=0;
}
unsigned long fixture_debug_register_read(int reg){
 if(reg!=6||!m14_dr6.active||!m14_dr6.vector||m14_dr6.calls++)m14_dr6.failed=1;
 m14_dr6.observed_before_read=m14_dr6.active->gpr.rflags;
 if(m14_dr6.observed_before_read!=m14_dr6.vector->saved_flags)m14_dr6.failed=1;
 return m14_dr6.vector->dr6;
}
int m14_debug_check_dr6_at_signal(const struct siginfo*info){
 if(!info||m14_dr6.calls!=1||m14_dr6.failed)return 1;
 if(info->si_code!=m14_dr6.vector->expected_code)return 1;
 if(m14_dr6.active->gpr.rflags!=m14_dr6.vector->expected_flags)return 1;
 /* Real producer storage must be initialized in full. Independent byte oracle
  * uses actual C int representation/offset; no uninitialized padding dump. */
 const unsigned char*got=(const unsigned char*)info;
 const unsigned char*code=(const unsigned char*)&m14_dr6.vector->expected_code;
 unsigned long off=__builtin_offsetof(struct siginfo,si_code);
 for(unsigned long i=0;i<sizeof(*info);i++){
  unsigned char want=(i>=off&&i<off+sizeof(int))?code[i-off]:0;
  if(got[i]!=want)return 1;
 }
 return 0;
}
unsigned m14_debug_state_vector_count(void){return sizeof(M14_DEBUG_STATES)/sizeof(M14_DEBUG_STATES[0]);}
const struct M14DebugStateVector*m14_debug_state_vector(unsigned n){
 return n<m14_debug_state_vector_count()?&M14_DEBUG_STATES[n]:0;
}
