/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * No real signals, waits, exits or process mutation; all use providers below.
 */
#include "fixture-prelude.h"
int debug;pid_t master_tid;
static jmp_buf frame;static int query_fail,wait_mode,wait_calls;
void sendsig(int sig,siginfo_t *i,void *c) {assert(0);}
int __wrap_sigaction(int sig,const struct sigaction *a,struct sigaction *old) {
 if(!a){assert(old);printf("query-action=%d,%d\n",sig,query_fail);if(query_fail)return -1;memset(old,0,sizeof(*old));old->sa_handler=(void*)0x6666;memset(&old->sa_mask,0x5a,sizeof(old->sa_mask));old->sa_flags=SA_RESTART|SA_NOCLDWAIT;old->sa_restorer=(void*)0x7777;return 0;}
 assert(!old);unsigned long first,last;memcpy(&first,&a->sa_mask,8);memcpy(&last,(char*)&a->sa_mask+sizeof(sigset_t)-8,8);
 printf("install-action=%d,%d,%x,%lx,%lx,%d\n",sig,a->sa_sigaction==sendsig?1:a->sa_handler==SIG_IGN?2:3,a->sa_flags,first,last,a->sa_restorer==(void*)0x7777?1:0);
 if(query_fail)assert(a->sa_sigaction==sendsig&&a->sa_flags==SA_SIGINFO&&first==0&&last==0&&!a->sa_restorer);
 return 0;
}
int __wrap_sigemptyset(sigset_t *s) {puts("empty-set");memset(s,0,sizeof(*s));return 0;}
int __wrap_sigdelset(sigset_t *s,int sig) {assert(sig==SIGURG);puts("remove-local-signal");((unsigned long*)s)[(sig-1)/64]&=~(1UL<<((sig-1)%64));return 0;}
int __wrap_sigprocmask(int how,const sigset_t *s,sigset_t *old) {assert(how==SIG_SETMASK&&!old);unsigned long first;memcpy(&first,s,8);printf("set-mask=%lx\n",first);for(size_t i=8;i<sizeof(*s);i++)assert(!((unsigned char*)s)[i]);return 0;}
int __wrap_waitid(idtype_t kind,id_t pid,siginfo_t *i,int opt) {
 assert(kind==P_PID&&pid==124&&opt==(WEXITED|WNOWAIT));wait_calls++;printf("waitid=%d,%d\n",wait_mode,wait_calls);
 if(wait_mode==0&&wait_calls<=2){errno=EINTR;return -1;}
 if(wait_mode==2){errno=ECHILD;return -1;}
 i->si_pid=wait_mode==1?0:126;return 0;
}
ssize_t __wrap_write(int fd,const void *p,size_t n) {assert(fd==12&&n==128);printf("write=%d,%zu\n",fd,n);return 17;}
__sighandler_t __wrap_signal(int sig,__sighandler_t h) {assert(h==SIG_DFL);printf("signal-default=%d\n",sig);return SIG_DFL;}
pid_t __wrap_getpid(void) {return 222;}
int __wrap_kill(pid_t p,int sig) {assert(p==222);printf("kill-provider=%d,%d\n",p,sig);return 0;}
unsigned __wrap_sleep(unsigned n) {assert(n==1);puts("sleep-provider");longjmp(frame,4);return 0;}
int __wrap_pause(void) {puts("pause-provider");return -1;}
void __wrap_exit(int code) {printf("exit-provider=%d\n",code);longjmp(frame,5);}
int __wrap_isatty(int fd) {printf("isatty-provider=%d\n",fd);return 7;}
int main(int argc,char **argv) {
 if(argc>1){query_fail=1;mcexec_init_sigaction_install_bridge(10);puts("rust-defined-query-failure-complete");return 0;}
 size_t abi[]={sizeof(siginfo_t),_Alignof(siginfo_t),offsetof(siginfo_t,si_signo),offsetof(siginfo_t,si_pid),sizeof(struct sigaction),_Alignof(struct sigaction),offsetof(struct sigaction,sa_handler),offsetof(struct sigaction,sa_mask),offsetof(struct sigaction,sa_flags),offsetof(struct sigaction,sa_restorer),sizeof(sigset_t),_Alignof(sigset_t)};
#ifdef RUST_IMPL
 extern void mcexec_signal_fixture_abi(size_t*);size_t rustabi[12];mcexec_signal_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<12;i++)printf("%zu,",abi[i]);puts("");
 siginfo_t info;memset(&info,0,sizeof info);info.si_pid=456;info.si_signo=12;assert(mcexec_sendsig_si_pid_bridge(&info)==456&&mcexec_sendsig_si_signo_bridge(&info)==12);
 mcexec_init_sigaction_set_master_tid_bridge(900);assert(master_tid==900);
 mcexec_init_sigaction_install_bridge(10);mcexec_act_sigaction_install_bridge(10,1);mcexec_act_sigaction_install_bridge(10,0);
 mcexec_act_sigprocmask_apply_bridge(~0UL);mcexec_act_sigprocmask_apply_bridge(0);
 for(wait_mode=0;wait_mode<3;wait_mode++) {wait_calls=0;errno=EIO;int error=-9;int ret=mcexec_waitid_pid_bridge(124,WEXITED|WNOWAIT,&error);printf("wait-result=%d,%d\n",ret,error);if(wait_mode==0)assert(ret==126&&error==EINTR);else if(wait_mode==1)assert(!ret&&error==EIO);else assert(ret==-1&&error==ECHILD);}
 wait_mode=1;wait_calls=0;assert(!mcexec_waitid_pid_bridge(124,WEXITED|WNOWAIT,NULL));
 assert(mcexec_act_signalfd4_write_bridge(12,&info,128)==17);mcexec_act_signalfd4_write_error_bridge();mcexec_wait4_error_bridge(124,-1,ECHILD);
 debug=0;mcexec_exit_debug_bridge(0x100,4);mcexec_exit_report_status_bridge(7);debug=1;mcexec_exit_debug_bridge(0x100,4);mcexec_exit_report_status_bridge(7);mcexec_exit_report_signal_bridge(9);assert(mcexec_exit_isatty_bridge(2)==7);
 mcexec_exit_replay_signal_bridge(15);int jump=setjmp(frame);if(!jump)mcexec_sendsig_default_action_bridge(12);assert(jump==4);
 jump=setjmp(frame);if(!jump)mcexec_exit_process_bridge(23);assert(jump==5);
 puts("signal-wait-exit-fixture-complete");return 0;
}
