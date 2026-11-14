/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only: no driver or second executable queue.
 */
#include <types.h>
#include <process.h>
#include <affinity.h>
#include <syscall.h>
#include <cls.h>
extern int arch_do_kill_direct_target_gate_result(struct process *,struct process *,struct thread *,int,unsigned long,unsigned long *);
extern void interrupt_syscall(struct thread *,int);
_Static_assert(sizeof(unsigned long)==8 && sizeof(long)==8 && sizeof(int)==4,"LP64");
_Static_assert(UTI_STATE_RUNNING_IN_LINUX==2 && PS_EXITED==0x10 && SIGCONT==18,"exact gate constants");
_Static_assert(__builtin_types_compatible_p(__typeof__(&release_thread),void (*)(struct thread *)),"real held-ref release ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&interrupt_syscall),void (*)(struct thread *,int)),"real forwarding ABI");
/* Original return and continue normalization only; body is unchanged. */
static unsigned long original_direct_target_gate(struct process *proc,struct process *tproc,struct thread *tthread,int sig,unsigned long irqstate,int *finished){
 *finished=1;
#include "original-direct-target-gate.ACTUAL.inc"
 *finished=0;return 0x123456789abcdef0UL;
}
static unsigned long Rust_direct_target_gate(struct process *proc,struct process *tproc,struct thread *tthread,int sig,unsigned long irqstate,int *finished){
 unsigned long result=0x123456789abcdef0UL;
 *finished=arch_do_kill_direct_target_gate_result(proc,tproc,tthread,sig,irqstate,&result);
 return result;
}
