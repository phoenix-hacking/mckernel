/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real headers/extracted original bodies, controlled noirq-lock/hold/IRQ endpoints.
 */
#include <types.h>
#include <affinity.h>
#include <process.h>
#include <errno.h>
#include <string.h>
#include <ihk/debug.h>
extern int printf(const char *,...);
extern size_t fixture_target_abi(size_t);
extern int arch_do_kill_thread_target_result(struct thread_hash *,int,int,int,void *,void *,struct process **,struct thread **,mcs_rwlock_lock_t **,struct list_head **);
extern int arch_do_kill_prepare_info_result(int,siginfo_t *,siginfo_t *,siginfo_t **);
static struct thread_hash table;
static struct thread target,noise;
static struct process proc,other;
static struct mcs_rwlock_node lock,updatelock;
static struct process *out_proc;
static struct thread *out_target;
static mcs_rwlock_lock_t *out_lock;
static struct list_head *out_head;
struct event {int kind,lock,node,status,pstatus;};
struct outcome {struct event events[10];int count,error,rc,irq,holds,logs,proc,target,plock,head,status,pstatus;};
static struct outcome result;
static int mutation,hold_result,depth;
static void zero(void *p,size_t n){unsigned char *s=p;while(n--)*s++=0;}
static int equal(const void *p,const void *q,size_t n){const unsigned char *a=p,*b=q;while(n--)if(*a++!=*b++)return 0;return 1;}
static int lockid(mcs_rwlock_lock_t *l){return l==&table.lock[5]?1:l==&proc.update_lock?2:l==&proc.threads_lock?3:0;}
static void event(int kind,mcs_rwlock_lock_t *l,void *node){
 struct event *e;if(result.count==10){result.error=1;return;}
 e=&result.events[result.count++];e->kind=kind;e->lock=lockid(l);e->node=node==&lock?1:node==&updatelock?2:0;e->status=target.status;e->pstatus=proc.status;
 if(!e->lock || !e->node)result.error=1;
}
void __mcs_rwlock_reader_lock_noirq(struct mcs_rwlock_lock *l,struct mcs_rwlock_node *node){
 int id=lockid(l);event(1,l,node);++depth;
 if(result.irq!=1 || depth!=id)result.error=1;
 if(id==2 && mutation==1)target.status=PS_EXITED;
 if(id==3 && mutation==2)proc.status=PS_ZOMBIE;
}
void __mcs_rwlock_reader_unlock_noirq(struct mcs_rwlock_lock *l,struct mcs_rwlock_node *node){
 event(2,l,node);if(depth!=lockid(l) || result.irq!=1)result.error=1;--depth;
}
void cpu_restore_interrupt(unsigned long irq){if(irq!=7 || result.irq!=1 || depth)result.error=1;result.irq=0;}
int hold_thread(struct thread *t){
 if(t!=&target || depth!=3 || result.irq!=1)result.error=1;
 ++result.holds;return hold_result;
}
int kprintf(const char *fmt,...){
 __builtin_va_list ap;const char *func;int rc,tid;
 __builtin_va_start(ap,fmt);func=__builtin_va_arg(ap,const char *);rc=__builtin_va_arg(ap,int);tid=__builtin_va_arg(ap,int);__builtin_va_end(ap);
 if(!equal(fmt,"%s: ERROR hold_thread returned %d,tid=%d\n",sizeof("%s: ERROR hold_thread returned %d,tid=%d\n")) || !equal(func,"do_kill",8) || rc!=hold_result || tid!=5)result.error=1;
 ++result.logs;return 0;
}
unsigned long do_kill(struct thread *thread,int pid,int tid,int sig,siginfo_t *info,int ptracecont){
 struct thread *tthread=NULL;struct process *tproc=NULL;struct thread_hash *thash=&table;
 int found=0,hash,rc;unsigned long irqstate=7;
 mcs_rwlock_lock_t *savelock=NULL;struct list_head *head=NULL;
#include "original-thread-target.ACTUAL.inc"
 out_proc=tproc;out_target=tthread;out_lock=savelock;out_head=head;return 0;
}
static int original_prepare(int sig,siginfo_t *info,siginfo_t *fallback,siginfo_t **selected){
 siginfo_t info0;
 /* Preserve actual local-body bytes, then copy local fallback to caller storage
  * only for observation; pointer result normalized to that caller storage. */
#include "original-prepare-info.ACTUAL.inc"
 if(info==&info0){size_t i;for(i=0;i<sizeof(info0);i++)((unsigned char*)fallback)[i]=((unsigned char*)&info0)[i];info=fallback;}
 *selected=info;return 0;
}
static void setup(int member,int status,int pstatus,int mut,int hret){
 int i;zero(&result,sizeof(result));zero(&table,sizeof(table));zero(&target,sizeof(target));zero(&noise,sizeof(noise));zero(&proc,sizeof(proc));zero(&other,sizeof(other));
 for(i=0;i<HASH_SIZE;i++)INIT_LIST_HEAD(&table.list[i]);
 proc.pid=101;other.pid=202;proc.status=pstatus;target.proc=&proc;target.tid=5;target.status=status;
 noise.proc=&other;noise.tid=78;noise.status=PS_RUNNING;
 INIT_LIST_HEAD(&noise.hash_list);INIT_LIST_HEAD(&target.hash_list);list_add_tail(&noise.hash_list,&table.list[5]);
 if(member)list_add_tail(&target.hash_list,&table.list[5]);
 out_proc=NULL;out_target=NULL;out_lock=NULL;out_head=NULL;mutation=mut;hold_result=hret;depth=0;result.irq=1;
}
static int run(int rust,int member,int pid,int status,int pstatus,int sig,int mut,int hret,struct outcome *out){
 int rc;setup(member,status,pstatus,mut,hret);
 if(rust){rc=arch_do_kill_thread_target_result(&table,pid,5,sig,&lock,&updatelock,&out_proc,&out_target,&out_lock,&out_head);if(rc)cpu_restore_interrupt(7);}
 else rc=(int)do_kill(NULL,pid,5,sig,NULL,0);
 result.rc=rc;result.proc=out_proc==&proc;result.target=out_target==&target;result.plock=out_lock==&target.sigpendinglock;result.head=out_head==&target.sigpending;result.status=target.status;result.pstatus=proc.status;
 if(depth || (rc==-ESRCH?result.irq!=0:result.irq!=1))result.error=1;
 if(rc==0){
  int canhold=target.status!=PS_EXITED && (sig==SIGKILL || (proc.status!=PS_EXITED && proc.status!=PS_ZOMBIE));
  if(result.holds!=canhold || result.logs!=(canhold && hret!=0) || result.target!=(canhold && hret==0))result.error=1;
  if(result.count!=6 || result.events[0].node!=1 || result.events[2].node!=1 || result.events[5].node!=1)result.error=1;
 }
 *out=result;return result.error;
}
int main(void){
 static struct outcome a,b;unsigned long cases=0,prep=0;
 int statuses[]={PS_RUNNING,PS_EXITED,PS_TRACED},pstatuses[]={PS_RUNNING,PS_EXITED,PS_ZOMBIE},pids[]={-1,101,202},sigs[]={12,SIGKILL},holds[]={0,-5,1};
 int member,p,s,t,g,m,h,signal,provided;size_t i;
 size_t values[]={sizeof(struct thread),_Alignof(struct thread),sizeof(struct process),_Alignof(struct process),sizeof(struct thread_hash),offsetof(struct thread_hash,list),offsetof(struct thread_hash,lock),sizeof(mcs_rwlock_lock_t),offsetof(struct thread,hash_list),offsetof(struct thread,tid),offsetof(struct thread,proc),offsetof(struct thread,status),offsetof(struct thread,sigpendinglock),offsetof(struct thread,sigpending),offsetof(struct process,pid),offsetof(struct process,status),offsetof(struct process,update_lock),offsetof(struct process,threads_lock),sizeof(siginfo_t),_Alignof(siginfo_t),offsetof(siginfo_t,si_signo),offsetof(siginfo_t,si_code),sizeof(struct list_head),HASH_SIZE,SI_KERNEL};
 for(i=0;i<25;i++)if(values[i]!=fixture_target_abi(i)){printf("FAIL ABI %lu\n",(unsigned long)i);return 1;}
 for(member=0;member<2;member++)for(p=0;p<3;p++)for(s=0;s<3;s++)for(t=0;t<3;t++)for(g=0;g<2;g++)for(m=0;m<3;m++)for(h=0;h<3;h++){
  int e0=run(0,member,pids[p],statuses[s],pstatuses[t],sigs[g],m,holds[h],&a),e1=run(1,member,pids[p],statuses[s],pstatuses[t],sigs[g],m,holds[h],&b);
  if(e0 || e1 || !equal(&a,&b,sizeof(a))){printf("FAIL target %lu\n",cases);return 1;}++cases;
 }
 for(signal=-2;signal<=66;signal++)for(provided=0;provided<2;provided++){
  siginfo_t x,y,input;siginfo_t *xp=(siginfo_t*)1,*yp=(siginfo_t*)1;int xr,yr;
  for(i=0;i<sizeof(x);i++){((unsigned char*)&x)[i]=((unsigned char*)&y)[i]=(unsigned char)(i+41);((unsigned char*)&input)[i]=(unsigned char)(i*17+9);}
  xr=original_prepare(signal,provided?&input:NULL,&x,&xp);yr=arch_do_kill_prepare_info_result(signal,provided?&input:NULL,&y,&yp);
  if(xr!=yr || !equal(&x,&y,sizeof(x)) || ((xp==&x)!=(yp==&y)) || ((xp==&input)!=(yp==&input)) || ((xp==(siginfo_t*)1)!=(yp==(siginfo_t*)1))){printf("FAIL prepare %d %d\n",signal,provided);return 1;}++prep;
 }
 printf("PASS actual_C_Rust_target cases=%lu prepare=%lu ABI=25 ordered_locks=1 reused_node=1\n",cases,prep);return 0;
}
