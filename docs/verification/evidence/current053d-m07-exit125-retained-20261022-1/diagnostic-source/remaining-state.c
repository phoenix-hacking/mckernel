#define _GNU_SOURCE
/* Functional user-case control glue, adapted from native-vector-enabled-state.c.
 * All live component operations are in reviewed assembly, never C compute or
 * calls into libc while seeded. No pkey allocation/mprotect or MPX bounds ops. */
#include <cpuid.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>
struct context {
 unsigned char *original,*seed,*seen,*alternate;
 uint32_t mask,offset,length;
 _Atomic int gate,ready;
 int pid,tid;
 uint32_t second_offset,second_length;
};
_Static_assert(offsetof(struct context,mask)==32,"mask ABI");
_Static_assert(offsetof(struct context,offset)==36,"offset ABI");
_Static_assert(offsetof(struct context,length)==40,"length ABI");
_Static_assert(offsetof(struct context,gate)==44,"gate ABI");
_Static_assert(offsetof(struct context,ready)==48,"ready ABI");
_Static_assert(offsetof(struct context,pid)==52,"pid ABI");
_Static_assert(offsetof(struct context,tid)==56,"tid ABI");
_Static_assert(offsetof(struct context,second_offset)==60,"second offset ABI");
_Static_assert(offsetof(struct context,second_length)==64,"second length ABI");
_Static_assert(sizeof(_Atomic int)==4,"futex ABI");
extern int remaining_access(struct context *),pkru_access(void);
extern int remaining_probe(struct context *,int);
extern long remaining_wake(struct context *,_Atomic int *);
extern void remaining_handler(int);
extern char access_save[],access_restore[],access_rdpkru[],access_wrpkru[],access_refused[];
struct context *remaining_active;
volatile sig_atomic_t remaining_signal_seen;
static volatile sig_atomic_t eligibility_active,eligibility_signal,eligibility_trap,eligibility_code;
volatile uintptr_t remaining_access_instruction;
static _Alignas(4096) unsigned char worker_stack[262144];
static int fail(const char *stage,int id,int code) {
 printf("REMAINING_FAIL component=%d stage=%s code=%d\n",id,stage,code);return 1;
}
/* Unexpected-fault evidence only. Fixed stack buffer, bounded scalar formatting
 * and one async-signal-safe write; neither stdio nor allocation in this path.
 * A short/failed diagnostic write still reaches the original exit125. */
static char *fault_decimal(char *p,int value) {
 unsigned int v=(unsigned int)value;char digits[10];unsigned int n=0;
 if(value<0){*p++='-';v=0u-v;}
 do{digits[n++]=(char)('0'+v%10u);v/=10u;}while(v);
 while(n){*p++=digits[--n];}return p;
}
static char *fault_hex(char *p,uintptr_t value) {
 static const char digits[]="0123456789abcdef";
 *p++='0';*p++='x';
 for(unsigned int n=2u*sizeof(value);n;n--)*p++=digits[(value>>((n-1u)*4u))&15u];
 return p;
}
static void fault_record(int signal,int trap,int error,siginfo_t *info,
                         uintptr_t pc,uintptr_t armed,int active,int known,int ud,int gp) {
 char buffer[384],*p=buffer;
 #define TEXT(s) do{const char *q=(s);for(unsigned int n=0;n<sizeof(s)-1u;n++)*p++=q[n];}while(0)
 #define DEC(s,v) do{TEXT(s);p=fault_decimal(p,(v));}while(0)
 #define HEX(s,v) do{TEXT(s);p=fault_hex(p,(v));}while(0)
 TEXT("REMAINING_FAULT_V1");DEC(" signal=",signal);DEC(" trap=",trap);
 DEC(" error=",error);DEC(" info=",info!=0);DEC(" code=",info?info->si_code:0);
 HEX(" pc=",pc);HEX(" armed=",armed);HEX(" addr=",info?(uintptr_t)info->si_addr:0);
 DEC(" eligibility=",active);DEC(" known=",known);DEC(" ud=",ud);DEC(" gp=",gp);
 TEXT("\n");ssize_t written=write(STDERR_FILENO,buffer,(size_t)(p-buffer));(void)written;
 #undef HEX
 #undef DEC
 #undef TEXT
}
static void fault_handler(int signal,siginfo_t *info,void *opaque) {
 ucontext_t *u=opaque;uintptr_t pc=(uintptr_t)u->uc_mcontext.gregs[REG_RIP];
 /* Only the currently armed instruction is recoverable. Checked, aligned,
  * CPU-layout-sized buffers and original XSAVE-produced headers exclude a
  * malformed operand as a permitted eligibility result. PF/AC never recover. */
 int trap=(int)u->uc_mcontext.gregs[REG_TRAPNO];
 int error=(int)u->uc_mcontext.gregs[REG_ERR];
 int known=pc==(uintptr_t)access_save || pc==(uintptr_t)access_restore ||
           pc==(uintptr_t)access_rdpkru || pc==(uintptr_t)access_wrpkru;
 int ud=signal==SIGILL && trap==6 && error==0 && info &&
        info->si_code==ILL_ILLOPN && (uintptr_t)info->si_addr==pc;
 int gp=signal==SIGSEGV && trap==13 && error==0 && info &&
        info->si_code==SI_KERNEL && info->si_addr==0;
 if(eligibility_active && pc==remaining_access_instruction && known && (ud||gp)) {
  eligibility_signal=signal;eligibility_trap=trap;eligibility_code=info->si_code;
  remaining_access_instruction=0;
  u->uc_mcontext.gregs[REG_RIP]=(greg_t)(uintptr_t)access_refused;return;
 }
 fault_record(signal,trap,error,info,pc,remaining_access_instruction,eligibility_active,known,ud,gp);
 _exit(125);
}
static void watchdog(int s) {(void)s;_exit(124);}
static void pause_poll(void) {const struct timespec p={0,1000000};(void)nanosleep(&p,0);}
static void *worker(void *ptr) {
 struct context *c=ptr;c->pid=(int)getpid();c->tid=(int)syscall(SYS_gettid);
 return (void *)(intptr_t)remaining_probe(c,1);
}
static unsigned char *area(size_t n) {
 void *p=0;if(posix_memalign(&p,64,n))return 0;memset(p,0,n);return p;
}
static int allocate(struct context *c,size_t n,uint32_t mask,unsigned off,unsigned len) {
 c->mask=mask;c->offset=off;c->length=len;
 c->original=area(n);c->seed=area(n);c->seen=area(n);c->alternate=area(n);
 return !c->original||!c->seed||!c->seen||!c->alternate;
}
static void dispose(struct context *c) {free(c->original);free(c->seed);free(c->seen);free(c->alternate);}
static void u64(unsigned char *p,uint64_t v) {memcpy(p,&v,8);}
static int seeds(struct context *c,int id,size_t n) {
 memcpy(c->seed,c->original,n);memcpy(c->alternate,c->original,n);
 u64(c->seed+512,c->mask);u64(c->alternate+512,c->mask);
 memset(c->seed+520,0,56);memset(c->alternate+520,0,56);
 unsigned char *p=c->seed+c->offset,*q=c->alternate+c->offset;
 if(id==3) {
  /* MPX 3+4 are always owned together, never mask8 alone. EN=0 and all
   * reserved bits zero while seeded: ordinary CALL cannot clear BNDREGS.
   * Canonical page-aligned bases are register values, never dereferenced. */
  for(unsigned i=0;i<4;i++){u64(p+16*i,0x1000+16*i);u64(p+16*i+8,~(uint64_t)(0x2000+16*i));u64(q+16*i,0x3000+16*i);u64(q+16*i+8,~(uint64_t)(0x4000+16*i));}
  memset(c->seed+c->second_offset,0,c->second_length);
  memset(c->alternate+c->second_offset,0,c->second_length);
  u64(c->seed+c->second_offset,0x1000);u64(c->alternate+c->second_offset,0x2000);
 } else {
  uint32_t old;memcpy(&old,c->original+c->offset,4);
  /* Clear only existing non-key0 restrictions: cannot deny any memory access.
   * Must obtain two distinct noninitial values without changing key0 bits.
   * No pkey syscall and no access-permission experiment occurs. */
  uint32_t bits=old&~3u,one=bits&(~bits+1u),rest=bits&~one,two=rest&(~rest+1u);
  if(!one||!two)return 1;
  uint32_t a=old&~one,b=old&~two;
  if(!a||!b||a==b)return 1;
  memset(p,0,c->length);memset(q,0,c->length);memcpy(p,&a,4);memcpy(q,&b,4);
 }
 return !memcmp(p,c->original+c->offset,c->length)||!memcmp(p,q,c->length);
}
int main(void) {
 struct sigaction a={0};a.sa_sigaction=fault_handler;a.sa_flags=SA_SIGINFO;
 if(sigemptyset(&a.sa_mask)||sigaction(SIGILL,&a,0)||sigaction(SIGSEGV,&a,0))return fail("fault-handler",0,errno);
 a.sa_flags=0;a.sa_handler=watchdog;if(sigaction(SIGALRM,&a,0))return fail("watchdog",0,errno);alarm(10);
 unsigned x,y,z,w,lo=0,hi=0;
 if(__get_cpuid_max(0,0)<13)return fail("cpuid",0,1);
 __cpuid_count(1,0,x,y,z,w);if((z&0x0c000000u)!=0x0c000000u)return fail("xsave-osxsave",0,1);
 __asm__ volatile("xgetbv":"=a"(lo),"=d"(hi):"c"(0));
 __cpuid_count(13,0,x,y,z,w);if(z<576||z>1048576)return fail("area",0,1);size_t n=((size_t)z+63u)&~(size_t)63;
 printf("REMAINING_XCR0 hi=%08x lo=%08x\n",hi,lo);
 unsigned applicable=0,inapplicable=0,stopped=0;
 for(int id_index=0;id_index<2;id_index++) {
  int id=(int[]){3,9}[id_index];uint32_t mask=id==3?24u:512u;
  __cpuid_count(7,0,x,y,z,w);int feature=id==9?!!(z&8):!!(y&(1u<<14));
  if(!feature||(lo&mask)!=mask) {
   printf("REMAINING component=%d INAPPLICABLE reason=not-enabled\n",id);
   if(id==3)puts("REMAINING component=4 INAPPLICABLE reason=not-enabled");
   inapplicable|=mask;continue;
  }
  __cpuid_count(13,id,x,y,z,w);unsigned len=x,off=y,defined=id==3?64u:id==4?16u:4u;
  if(off<576||len<(id==3?64u:id==4?16u:8u)||off>n||len>n-off||(z&1))return fail("layout",id,1);
  struct context c={0},helper={0};if(allocate(&c,n,mask,off,defined)||allocate(&helper,n,mask,off,defined))return fail("allocation",id,1);
  if(id==3) {
   __cpuid_count(13,4,x,y,z,w);
   if(y<576||x<16||y>n||x>n-y||(z&1)||!(y+16<=off||off+64<=y))return fail("layout-pair",id,1);
   c.second_offset=helper.second_offset=y;c.second_length=helper.second_length=16;
  }
  eligibility_active=1;eligibility_signal=eligibility_trap=eligibility_code=0;remaining_access_instruction=0;int access=id==9?pkru_access():0;
  if(!access) { access=remaining_access(&c); }
  eligibility_active=0;remaining_access_instruction=0;
  if(access) {
   if(!eligibility_signal)return fail("unclassified-access",id,1);
   printf("REMAINING component=%d INAPPLICABLE reason=instruction-fault signal=%d trap=%d code=%d\n",id,eligibility_signal,eligibility_trap,eligibility_code);
   if(id==3)printf("REMAINING component=4 INAPPLICABLE reason=instruction-fault signal=%d trap=%d code=%d\n",eligibility_signal,eligibility_trap,eligibility_code);
   inapplicable|=mask;dispose(&c);dispose(&helper);continue;
  }
  if(seeds(&c,id,n)) {
   if(id!=9)return fail("safe-noninitial-seed",id,1);
   puts("REMAINING component=9 STOP reason=no-safe-noninitial-seed");
   stopped|=mask;dispose(&c);dispose(&helper);continue;
  }
  memcpy(helper.seed,c.alternate,n);memcpy(helper.alternate,c.seed,n);
  c.pid=(int)getpid();c.tid=(int)syscall(SYS_gettid);
  int rc=remaining_probe(&c,0);if(rc)return fail("syscall",id,rc);
  pthread_attr_t attr;pthread_t thread;
  if((rc=pthread_attr_init(&attr))||(rc=pthread_attr_setstack(&attr,worker_stack,sizeof(worker_stack)))||(rc=pthread_create(&thread,&attr,worker,&c))||(rc=pthread_attr_destroy(&attr)))return fail("thread",id,rc);
  int ready=0;for(int k=0;k<2000;k++){if(atomic_load_explicit(&c.ready,memory_order_acquire)){ready=1;break;}pause_poll();}if(!ready)return fail("ready",id,1);
  int woke=0;for(int k=0;k<2000;k++){long r=remaining_wake(&helper,&c.gate);if(r==1){woke=1;break;}if(r!=0)return fail("wake",id,(int)r);pause_poll();}if(!woke)return fail("not-queued",id,1);
  void *out;if((rc=pthread_join(thread,&out)))return fail("join",id,rc);if((rc=(int)(intptr_t)out))return fail("futex",id,rc);
  a.sa_handler=remaining_handler;if(sigaction(SIGUSR1,&a,0))return fail("signal-install",id,errno);
  remaining_active=&c;c.pid=(int)getpid();c.tid=(int)syscall(SYS_gettid);
  sigset_t unblocked;sigemptyset(&unblocked);sigaddset(&unblocked,SIGUSR1);if((rc=pthread_sigmask(SIG_UNBLOCK,&unblocked,0)))return fail("signal-mask",id,rc);
  if((rc=remaining_probe(&c,2)))return fail("signal",id,rc);
  printf("REMAINING component=%d ACCESS_ROUNDTRIP_SYSCALL_QUEUED_FUTEX_SIGNAL_RESTORE_PASS\n",id);if(id==3)puts("REMAINING component=4 ACCESS_ROUNDTRIP_SYSCALL_QUEUED_FUTEX_SIGNAL_RESTORE_PASS");applicable|=mask;dispose(&c);dispose(&helper);
 }
 alarm(0);printf("REMAINING_COMPLETED applicable=%03x inapplicable=%03x stopped=%03x\n",applicable,inapplicable,stopped);return stopped?2:0;
}
