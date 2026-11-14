/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual original legacy/native C against exact public Rust policy.
 * Real headers supply all original syscall and signal constants.
 */
#include <syscall.h>
#include <signal.h>
#include <errno.h>
extern int printf(const char *,...);
extern int arch_signal_restart_result(int,unsigned long,int,int,int);
extern unsigned long fixture_restart_actual_Rust_ABI(unsigned long);
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(unsigned long)==8,"realLP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_signal_restart_result),int (*)(int,unsigned long,int,int,int)),"realpublicpolicyABI");
#undef MCKERNEL_NATIVE_SIGNAL_STACK
#define isrestart original_legacy_isrestart
#include "original-isrestart.ACTUAL.inc"
#undef isrestart
#define MCKERNEL_NATIVE_SIGNAL_STACK 1
#define isrestart original_native_isrestart
#include "original-isrestart.ACTUAL.inc"
#undef isrestart
static int compare_num(int num,unsigned long *checked)
{
 const unsigned long returns[]={0,1,(unsigned long)-EINTR,(unsigned long)-EFAULT,~0UL,1UL<<63};
 const int signals[]={-1,0,1,SIGKILL,SIGCHLD,SIGSTOP,64,65};
 const int restarts[]={(-2147483647-1),-1,0,1,0x10000000};
 for(unsigned long r=0;r<6;r++)for(unsigned long s=0;s<8;s++)for(unsigned long a=0;a<5;a++)for(int native=0;native<2;native++) {
  int old=native?original_native_isrestart(num,returns[r],signals[s],restarts[a]):original_legacy_isrestart(num,returns[r],signals[s],restarts[a]);
  int rust=arch_signal_restart_result(num,returns[r],signals[s],restarts[a],native);
  if(old!=rust){printf("FAIL restart num=%d rc=%lx sig=%d flag=%d native=%d old=%d rust=%d\n",num,returns[r],signals[s],restarts[a],native,old,rust);return 1;}
  (*checked)++;
 }
 return 0;
}
int main(void)
{
 unsigned long checked=0;
 const unsigned long actualABI[]={sizeof(int),sizeof(long),sizeof(unsigned long),EINTR,SIGKILL,SIGSTOP,SIGCHLD,__NR_rt_sigreturn,
 __NR_pause,__NR_rt_sigsuspend,__NR_rt_sigtimedwait,__NR_epoll_wait,__NR_epoll_pwait,__NR_poll,__NR_ppoll,__NR_select,__NR_pselect6,__NR_msgrcv,__NR_msgsnd,__NR_semop,__NR_semtimedop,__NR_clock_nanosleep,__NR_nanosleep,__NR_io_getevents};
 for(unsigned long i=0;i<sizeof actualABI/sizeof actualABI[0];i++)if(actualABI[i]!=fixture_restart_actual_Rust_ABI(i))return 3;
 for(int n=-3;n<=512;n++)if(compare_num(n,&checked))return 1;
 if(compare_num((-2147483647-1),&checked)||compare_num(2147483647,&checked))return 1;
 printf("PASS actual_legacy_native_C_vs_Rust_restart vectors=%lu unsigned_return_bits=1 shortcut_order=1\n",checked);return checked==248640?0:2;
}
