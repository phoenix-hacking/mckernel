/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Existing find/unlock/waitq providers are explicit scalar/identity HOST mocks.
 * No actual lookup, lock, wait list, wake, scheduler, reference or kernel effect. */
#include <types.h>
#include <string.h>
#include <arch-memory.h>
#include <registers.h>
#include <signal.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <waitq.h>
#include <ihk/debug.h>
extern int puts(const char *);
extern int printf(const char *,...);
_Static_assert(__builtin_types_compatible_p(__typeof__(&find_thread),struct thread *(*)(int,int)),"genuine find signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&thread_unlock),void (*)(struct thread *)),"genuine unlock signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&waitq_wakeup),void (*)(waitq_t *)),"genuine waitq signature");
static struct thread threads[3];static waitq_t queues[3];
static int expected_tgid,expected_tid,calls,fault;
static struct thread *find_result,*unlock_expected,*unlock_seen;
static waitq_t *wake_expected,*wake_seen;
struct thread *f03_three_fixture_find(int tgid,int tid){++calls;if(tgid!=expected_tgid||tid!=expected_tid)fault=1;return find_result;}
void f03_three_fixture_unlock(struct thread *t){++calls;if(t!=unlock_expected||unlock_seen)fault=1;unlock_seen=t;}
void f03_three_fixture_wake(waitq_t *q){++calls;if(q!=wake_expected||wake_seen)fault=1;wake_seen=q;}
#define find_thread f03_three_fixture_find
#define thread_unlock f03_three_fixture_unlock
#define waitq_wakeup f03_three_fixture_wake
#define ptrace_wakeup_find_thread_bridge original_wakeup_find
#include "01-ptrace_wakeup_find_thread_bridge/original.C.inc"
#undef ptrace_wakeup_find_thread_bridge
#include "01-ptrace_wakeup_find_thread_bridge/paired-selector.C.inc"
#ifndef ptrace_wakeup_find_thread_bridge
#error "actual selected wakeup find branch required"
#endif
#define ptrace_wakeup_thread_unlock_bridge original_wakeup_unlock
#include "02-ptrace_wakeup_thread_unlock_bridge/original.C.inc"
#undef ptrace_wakeup_thread_unlock_bridge
#include "02-ptrace_wakeup_thread_unlock_bridge/paired-selector.C.inc"
#ifndef ptrace_wakeup_thread_unlock_bridge
#error "actual selected wakeup unlock branch required"
#endif
#define thread_exit_waitq_wake_bridge original_exit_waitq_wake
#include "03-thread_exit_waitq_wake_bridge/original.C.inc"
#undef thread_exit_waitq_wake_bridge
#include "03-thread_exit_waitq_wake_bridge/paired-selector.C.inc"
#ifndef thread_exit_waitq_wake_bridge
#error "actual selected exit waitq branch required"
#endif
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_wakeup_find_thread_bridge),unsigned long (*)(int,int)),"selected find ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_wakeup_thread_unlock_bridge),void (*)(unsigned long)),"selected unlock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&thread_exit_waitq_wake_bridge),void (*)(void *)),"selected wake ABI");
extern const unsigned long F03_THREE_WAKE_PROVIDER_ABI[19];
static int abi(void){const unsigned long c[19]={sizeof(struct thread),__alignof__(struct thread),sizeof(int),__alignof__(int),sizeof(unsigned long),__alignof__(unsigned long),sizeof(void *),__alignof__(void *),sizeof(unsigned long (*)(int,int)),sizeof(void (*)(unsigned long)),sizeof(void (*)(void *)),sizeof(waitq_t),__alignof__(waitq_t),__builtin_offsetof(waitq_t,lock),__builtin_offsetof(waitq_t,waitq),sizeof(ihk_spinlock_t),__alignof__(ihk_spinlock_t),sizeof(struct list_head),__alignof__(struct list_head)};unsigned i;for(i=0;i<19;i++)if(c[i]!=F03_THREE_WAKE_PROVIDER_ABI[i]){printf("ABI FAIL %u C=%lu Rust=%lu\n",i,c[i],F03_THREE_WAKE_PROVIDER_ABI[i]);return 0;}return 1;}
static int find_pairs(void){const int tgids[5]={0,1,-1,2147483647,(-2147483647-1)},tids[6]={0,1,2,-1,2147483647,(-2147483647-1)};unsigned i,j,k,n=0;unsigned long a,b;unsigned long (*selected)(int,int)=ptrace_wakeup_find_thread_bridge;if(selected!=f03_ptrace_io_find)return 0;for(i=0;i<5;i++)for(j=0;j<6;j++)for(k=0;k<3;k++){expected_tgid=tgids[i];expected_tid=tids[j];find_result=k?&threads[k-1]:0;calls=fault=0;a=original_wakeup_find(expected_tgid,expected_tid);if(calls!=1||fault||a!=(unsigned long)find_result)return 0;calls=fault=0;b=selected(expected_tgid,expected_tid);if(calls!=1||fault||b!=a)return 0;++n;}return n==90;}
static int unlock_pairs(void){unsigned i;void (*selected)(unsigned long)=ptrace_wakeup_thread_unlock_bridge;if(selected!=f03_ptrace_io_unlock)return 0;for(i=0;i<3;i++){unlock_expected=&threads[i];unlock_seen=0;calls=fault=0;original_wakeup_unlock((unsigned long)unlock_expected);if(calls!=1||fault||unlock_seen!=unlock_expected)return 0;unlock_seen=0;calls=fault=0;selected((unsigned long)unlock_expected);if(calls!=1||fault||unlock_seen!=unlock_expected)return 0;}return 1;}
static int wake_pairs(void){unsigned i;waitq_t original;void (*selected)(void *)=thread_exit_waitq_wake_bridge;if(selected!=f03_exit_notify_wake)return 0;for(i=0;i<3;i++){__builtin_memcpy(&original,&queues[i],sizeof original);wake_expected=&queues[i];wake_seen=0;calls=fault=0;original_exit_waitq_wake(wake_expected);if(calls!=1||fault||wake_seen!=wake_expected||__builtin_memcmp(&original,&queues[i],sizeof original))return 0;wake_seen=0;calls=fault=0;selected(wake_expected);if(calls!=1||fault||wake_seen!=wake_expected||__builtin_memcmp(&original,&queues[i],sizeof original))return 0;}return 1;}
int main(void){if(!abi()||!find_pairs()||!unlock_pairs()||!wake_pairs())return 1;puts("PASS three reused callbacks:90 find +3 unlock +3 waitq pointer-forwarding pairs +19 genuine ABI words; explicit HOST mocks only; real lookup/lock/wake/lifetime ownership OPEN");return 0;}
