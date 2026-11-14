/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual reference bodies and real headers. CPU/IRQ/signal effects controlled;
 * the allocator, locks, list and byte primitives are actual Rust implementations.
 */
#include <types.h>
#include <process.h>
#include <affinity.h>
#include <syscall.h>
#include <cls.h>
#include <kmalloc.h>
#include <errno.h>
#include <string.h>
extern int printf(const char *,...);
extern void *fixture_host_byte_memset(void *,int,size_t) __asm__("memset");
extern int memcmp(const void *,const void *,size_t);
extern int arch_do_kill_process_group_result(struct thread *,int,int,siginfo_t *,int,struct process_hash *);
extern int arch_do_kill_pending_enqueue_result(struct thread *,struct list_head *,unsigned long,int,const siginfo_t *,int,int *);
extern size_t fixture_group_pending_actual_Rust_ABI(size_t);
extern void fixture_reset_genuine_arena(void);
_Static_assert(sizeof(long)==8 && sizeof(int)==4 && sizeof(void*)==8,"LP64");
_Static_assert(sizeof(struct sig_pending)==160 && sizeof(siginfo_t)==128,"pending representation");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kmalloc_tracked),void *(*)(int,ihk_mc_ap_flag,char *,int)),"tracked allocator real ABI");
static struct cpu_local_var localcpu;
static struct process_hash table;
static struct process procs[9];
static struct thread caller,target;
static unsigned char arena[65536] __attribute__((aligned(64)));
static int irqdepth,preemptdepth,provider_error,fail_alloc,schedule,mutated,return_mode;
static int delivered[20],ndelivered,oom_logs;
struct cpu_local_var *fixture_cpu(void){return &localcpu;}
void *fixture_arena(void){return arena;}
int ihk_mc_get_processor_id(void){return 0;}
void fixture_provider_error(void){provider_error=1;}
void preempt_disable(void){++preemptdepth;}
void preempt_enable(void){if(preemptdepth<=0)provider_error=1;--preemptdepth;}
void cpu_pause(void){provider_error=1;}
unsigned long cpu_disable_interrupt_save(void){unsigned long old=(unsigned long)irqdepth;++irqdepth;return old;}
void cpu_restore_interrupt(unsigned long f){if(irqdepth!=(int)f+1)provider_error=1;irqdepth=(int)f;}
int kprintf(const char *fmt,...){(void)fmt;++oom_logs;return 0;}
int fixture_fail_alloc(void){
 if(schedule && !mutated){
  if(irqdepth || preemptdepth)provider_error=1;
  mutated=1;
  if(schedule==1 && procs[1].hash_list.next!=&procs[1].hash_list)list_del_init(&procs[1].hash_list);
  if(schedule==2)list_add_tail(&procs[8].hash_list,&table.list[0]);
 }
 return fail_alloc;
}
unsigned long do_kill(struct thread *t,int pid,int tid,int sig,siginfo_t *info,int pc){
 if(irqdepth || preemptdepth || tid!=-1 || sig!=12 || pc!=2 || !info || info->si_signo!=12 || (t && t!=&caller))provider_error=1;
 if(ndelivered>=20){provider_error=1;return 0;}
 delivered[ndelivered++]=pid;
 if(return_mode==0)return 0;
 if(return_mode==1)return (unsigned long)(-pid);
 return 0x8123456700000000UL | ((unsigned int)pid ^ 0x80000000U);
}
static int original_group(struct thread *thread,int pid,int sig,siginfo_t *info,int ptracecont,struct process_hash *phash){
 int i,tid=-1;
#include "original-group.ACTUAL.inc"
 return -EINVAL;
}
static int original_pending(struct thread *tthread,struct list_head *head,unsigned long mask,int sig,const siginfo_t *info,int ptracecont,int *out){
 struct sig_pending *pending=NULL;int doint=*out,rc=0;
#include "original-pending.ACTUAL.inc"
 *out=doint;return rc;
}
struct outcome {int rc,doint,event,delivered[20],n,errors,irq,preempt,oom,nodes,interrupted[4],pc[4];unsigned long masks[4];unsigned char info[4][128];};
static void common_reset(void){
 fixture_host_byte_memset(&localcpu,0,sizeof(localcpu));fixture_host_byte_memset(&caller,0,sizeof(caller));fixture_host_byte_memset(&target,0,sizeof(target));
 irqdepth=preemptdepth=provider_error=mutated=ndelivered=oom_logs=0;fixture_reset_genuine_arena();
}
static void reset_group(int count,int s){
 int i;common_reset();fixture_host_byte_memset(&table,0,sizeof(table));fixture_host_byte_memset(procs,0,sizeof(procs));
 for(i=0;i<HASH_SIZE;i++){INIT_LIST_HEAD(&table.list[i]);mcs_rwlock_init(&table.lock[i]);}
 for(i=0;i<9;i++){procs[i].pid=100+i;procs[i].pgid=i%2?7:8;INIT_LIST_HEAD(&procs[i].hash_list);}
 procs[0].pgid=7;procs[8].pgid=7;caller.proc=&procs[0];
 for(i=0;i<count;i++)list_add_tail(&procs[i].hash_list,&table.list[i%3]);
 schedule=s;
}
static void get_common(struct outcome *o){
 o->errors=provider_error;o->irq=irqdepth;o->preempt=preemptdepth;o->oom=oom_logs;o->n=ndelivered;
 memcpy(o->delivered,delivered,(size_t)ndelivered*sizeof(int));
}
static int group_case(int which,int pid,int count,int hasthread,int fail,int mutation,int ret,struct outcome *o){
 siginfo_t info;fixture_host_byte_memset(o,0,sizeof(*o));reset_group(count,mutation);fail_alloc=fail;return_mode=ret;
 fixture_host_byte_memset(&info,0,sizeof(info));info.si_signo=12;
 o->rc=which?arch_do_kill_process_group_result(hasthread?&caller:NULL,pid,12,&info,2,&table):original_group(hasthread?&caller:NULL,pid,12,&info,2,&table);
 get_common(o);return 0;
}
static void snapshot_pending(struct outcome *o,struct list_head *head){
 struct list_head *p;int n=0;
 for(p=head->next;p!=head;p=p->next){
  struct sig_pending *q=list_entry(p,struct sig_pending,list);
  if(n==4 || p->next->prev!=p || p->prev->next!=p){provider_error=1;break;}
  o->masks[n]=q->sigmask.__val[0];o->pc[n]=q->ptracecont;o->interrupted[n]=q->interrupted;memcpy(o->info[n],&q->info,128);++n;
 }
 o->nodes=n;
}
static int pending_case(int which,int sig,int pc,int existing,int fail,int pattern,struct outcome *o){
 struct list_head head;struct sig_pending *old;struct mcs_rwlock_node lock;siginfo_t info;unsigned long mask=1UL<<(sig-1);int j,doint=0;
 common_reset();schedule=0;fail_alloc=0;fixture_host_byte_memset(o,0,sizeof(*o));INIT_LIST_HEAD(&head);mcs_rwlock_init(&target.sigpendinglock);
 for(j=0;j<128;j++)((unsigned char*)&info)[j]=(unsigned char)(j*17+pattern);
 if(existing){
  old=kmalloc_tracked(sizeof(*old),IHK_MC_AP_NOWAIT,__FILE__,__LINE__);
  if(!old)return 1;
  memset(old,0,sizeof(*old));old->sigmask.__val[0]=existing==1?mask:mask^0x8000000000000000UL;
  old->ptracecont=existing==3?pc^1:pc;old->interrupted=23;
  for(j=0;j<128;j++)((unsigned char*)&old->info)[j]=(unsigned char)(j+81);
  list_add_tail(&old->list,&head);
 }
 fail_alloc=fail;
 /* The original do_kill caller owns IRQ-disabled state + writer lock. */
 {unsigned long flags=cpu_disable_interrupt_save();mcs_rwlock_writer_lock_noirq(&target.sigpendinglock,&lock);
 o->rc=which?arch_do_kill_pending_enqueue_result(&target,&head,mask,sig,&info,pc,&doint):original_pending(&target,&head,mask,sig,&info,pc,&doint);
 if(irqdepth!=1 || preemptdepth!=1)provider_error=1;
 mcs_rwlock_writer_unlock_noirq(&target.sigpendinglock,&lock);cpu_restore_interrupt(flags);}
 o->doint=doint;o->event=target.sigevent;snapshot_pending(o,&head);
 /* Follow protected consumer ownership: unlink before releasing actual memory. */
 while(!list_empty(&head)){old=list_entry(head.next,struct sig_pending,list);list_del(&old->list);kfree_tracked(old,__FILE__,__LINE__);}
 get_common(o);return 0;
}
int main(void){
 static struct outcome a,b;unsigned long groups=0,pendings=0;int p,c,h,f,m,r,s,pc,e,t;
 size_t abi[]={sizeof(struct thread),_Alignof(struct thread),sizeof(struct process),_Alignof(struct process),sizeof(struct process_hash),offsetof(struct process_hash,list),offsetof(struct process_hash,lock),HASH_SIZE,sizeof(struct sig_pending),offsetof(struct sig_pending,info),offsetof(struct sig_pending,ptracecont),offsetof(struct sig_pending,interrupted),sizeof(siginfo_t),sizeof(struct kmalloc_header),offsetof(struct cpu_local_var,free_list),offsetof(struct thread,sigevent),offsetof(struct process,hash_list),sizeof(mcs_rwlock_lock_t)};
 const int pids[]={0,-1,-7,-8,-9};const int sigs[]={1,9,19,32,33,64};
 for(t=0;t<18;t++)if(abi[t]!=fixture_group_pending_actual_Rust_ABI((size_t)t)){printf("FAIL ABI %d\n",t);return 1;}
 for(p=0;p<5;p++)for(c=0;c<=5;c++)for(h=0;h<2;h++)for(f=0;f<2;f++)for(m=0;m<3;m++)for(r=0;r<3;r++){
  group_case(0,pids[p],c,h,f,m,r,&a);group_case(1,pids[p],c,h,f,m,r,&b);
  if(memcmp(&a,&b,sizeof(a)) || a.errors || a.irq || a.preempt){printf("FAIL group %lu p%d c%d h%d f%d m%d r%d\n",groups,p,c,h,f,m,r);return 1;}++groups;
 }
 for(s=0;s<6;s++)for(pc=0;pc<2;pc++)for(e=0;e<4;e++)for(f=0;f<2;f++)for(t=0;t<2;t++){
  if(pending_case(0,sigs[s],pc,e,f,t,&a) || pending_case(1,sigs[s],pc,e,f,t,&b) || memcmp(&a,&b,sizeof(a)) || a.errors || a.irq || a.preempt){printf("FAIL pending %lu s%d pc%d e%d f%d t%d\n",pendings,s,pc,e,f,t);return 1;}++pendings;
 }
 printf("PASS actual_C_Rust_group_pending group=%lu pending=%lu ABI=18 genuine_lock_list_tracked_local_allocator=1\n",groups,pendings);return 0;
}
