/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Deterministic providers only. No real fork/thread/signal/ioctl/mmap.
 */
#include "fixture-prelude.h"
int fd,ischild,debug,n_threads;
char dev[32]="/dev/mcos0";
void *thread_data;
struct fork_sync_container *fork_sync_top;
pthread_mutex_t fork_sync_mutex;
static jmp_buf exit_frame;
static int open_rc,ppd_rc,pool_rc,worker_rc,parent_dead,yields,posts,unmaps,frees,map_fail,alloc_fail,sem_rc;
static int map_count;static void *maps[8];static int alive[8];
static struct fork_sync *self;
void *__real_malloc(size_t);void __real_free(void *);
void *__wrap_malloc(size_t n) {if(alloc_fail){alloc_fail=0;return NULL;}return __real_malloc(n);}
void __wrap_free(void *p) {if(p){frees++;printf("free-node\n");}__real_free(p);}
void *__wrap_mmap(void *p,size_t n,int prot,int flags,int x,off_t off) {
 assert(!p&&n==sizeof(struct fork_sync)&&prot==(PROT_READ|PROT_WRITE)&&flags==(MAP_SHARED|MAP_ANONYMOUS)&&x==-1&&!off);
 if(map_fail){map_fail=0;return MAP_FAILED;}
 void *q=__real_malloc(n);memset(q,0xa5,n);maps[map_count]=q;alive[map_count++]=1;printf("map=%zu\n",n);return q;
}
int __wrap_munmap(void *p,size_t n) {assert(n==sizeof(struct fork_sync));for(int i=0;i<map_count;i++)if(maps[i]==p&&alive[i]){alive[i]=0;unmaps++;printf("unmap=%d\n",i);return 0;}assert(0);return -1;}
int __wrap_sem_init(sem_t *p,int shared,unsigned value) {assert(shared==1&&!value);struct fork_sync *f=(void*)((char*)p - offsetof(struct fork_sync,sem));assert(!f->status&&!f->success);printf("sem-init=%d\n",sem_rc);return sem_rc;}
int __wrap_sem_post(sem_t *p) {assert(p==&self->sem);posts++;puts("sem-post");return 0;}
int __wrap_sem_destroy(sem_t *p) {assert(p==&self->sem);puts("sem-destroy");return 0;}
int __wrap_sem_trywait(sem_t *p) {assert(p==&self->sem);errno=EAGAIN;puts("sem-trywait");return -1;}
int __wrap_pthread_mutex_init(pthread_mutex_t *p,const pthread_mutexattr_t *a) {assert(p==&fork_sync_mutex&&!a);puts("mutex-init");return 0;}
int __wrap_pthread_mutex_lock(pthread_mutex_t *p) {assert(p==&fork_sync_mutex);puts("mutex-lock");return 0;}
int __wrap_pthread_mutex_unlock(pthread_mutex_t *p) {assert(p==&fork_sync_mutex);puts("mutex-unlock");return 0;}
int __wrap_close(int f) {printf("close=%d\n",f);return 0;}
int mcexec_opendev_body(void) {printf("opendev=%d\n",open_rc);errno=EACCES;return open_rc;}
char *mcexec_opendev_dev_bridge(void) {return dev;}
int __wrap_ioctl(int f,unsigned long request,...) {assert(f==42);if(request==MCEXEC_UP_CREATE_PPD){va_list ap;va_start(ap,request);struct rpgtable_desc *p=va_arg(ap,void*);va_end(ap);assert(p->start==0x1000&&p->len==0x2000&&p->rpgtable==0x3000);printf("create-ppd=%d\n",ppd_rc);errno=EINVAL;return ppd_rc;}assert(request==MCEXEC_UP_GET_NUM_POOL_THREADS);printf("pool-count=%d\n",pool_rc);return pool_rc;}
void init_sigaction(void) {puts("signals-init");}
int init_worker_threads(int f) {assert(f==42&&!thread_data);printf("workers=%d,%d\n",n_threads,worker_rc);return worker_rc;}
void mcexec_join_all_threads_body(void) {puts("join-all");}
pid_t __wrap_getpid(void) {return 100;}
pid_t __wrap_getppid(void) {puts("parent-check");return parent_dead?1:99;}
int __wrap_sched_yield(void) {yields++;puts("yield");if(yields==2)self->success=1;return 0;}
pid_t __wrap_fork(void) {puts("fork-provider");return 123;}
pid_t __wrap_waitpid(pid_t pid,int *st,int opt) {assert(pid==123&&opt==WNOHANG);*st=0;puts("waitpid-provider");return 123;}
void __wrap_exit(int code) {printf("exit=%d\n",code);longjmp(exit_frame,code+1);}
static void clear_all(void) {
 while(fork_sync_top){struct fork_sync_container *p=fork_sync_top;fork_sync_top=p->next;__real_free(p);}
 for(int i=0;i<map_count;i++)__real_free(maps[i]);map_count=0;
}
static struct fork_sync_container *node(struct fork_sync *fs,struct fork_sync_container *next) {struct fork_sync_container *n=__real_malloc(sizeof(*n));n->pid=9;n->fs=fs;n->next=next;return n;}
int main(void) {
 size_t abi[]={sizeof(struct fork_sync),_Alignof(struct fork_sync),offsetof(struct fork_sync,sem),sizeof(struct fork_sync_container),_Alignof(struct fork_sync_container),offsetof(struct fork_sync_container,next),offsetof(struct fork_sync_container,fs),sizeof(struct rpgtable_desc),offsetof(struct rpgtable_desc,start),offsetof(struct rpgtable_desc,len)};
#ifdef RUST_IMPL
 extern void mcexec_clone_fixture_abi(size_t*);size_t other[10];mcexec_clone_fixture_abi(other);assert(!memcmp(abi,other,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<10;i++)printf("%zu,",abi[i]);puts("");
 map_fail=1;assert(!mcexec_clone_alloc_fork_sync_bridge());alloc_fail=1;assert(!mcexec_clone_alloc_container_bridge());
 void *container=mcexec_clone_alloc_container_bridge();for(size_t i=0;i<sizeof(struct fork_sync_container);i++)assert(!((unsigned char*)container)[i]);mcexec_fork_sync_free_bridge(container);
 for(int mode=0;mode<7;mode++) {
 printf("case=%d\n",mode);fd=7;ischild=0;thread_data=(void*)1;n_threads=6;open_rc=42;ppd_rc=0;pool_rc=3;worker_rc=0;parent_dead=0;yields=posts=unmaps=frees=0;
 if(mode==1)open_rc=-1;if(mode==2)ppd_rc=-1;if(mode==3)pool_rc=-1;if(mode==4)worker_rc=-EAGAIN;if(mode==5)parent_dead=1;if(mode==6)pool_rc=1;
 self=mcexec_clone_alloc_fork_sync_bridge();assert(self);struct fork_sync *other=mcexec_clone_alloc_fork_sync_bridge();
 fork_sync_top=node(other,node(self,node(NULL,NULL)));
 struct syscall_wait_desc w={0};w.sr.args[1]=0x1000;w.sr.args[2]=0x2000;w.sr.args[3]=0x3000;
 int escaped=setjmp(exit_frame);
 if(!escaped) {long ret=mcexec_clone_child_bridge(&w,self);printf("return=%ld\n",ret);assert(!ret);}
 printf("state=%d,%d,%d,%d,%d,%d,%d\n",ischild,n_threads,self->status,yields,posts,unmaps,frees);
 assert(ischild==1);
 if(mode==4)assert(escaped==2&&fork_sync_top&&posts==0&&frees==0);
 else {assert(!fork_sync_top&&posts==1&&frees==3);if(mode==1)assert(self->status==-EACCES&&escaped==2);else if(mode==2)assert(self->status==-EINVAL&&escaped==2);else if(mode==5)assert(escaped==2&&unmaps==1);else assert(!escaped&&unmaps==2);}
 clear_all();
 }
 self=mcexec_clone_alloc_fork_sync_bridge();assert(mcexec_clone_sem_trywait_bridge(self)==-1&&errno==EAGAIN);mcexec_clone_sem_destroy_bridge(self);mcexec_fork_sync_lock_bridge();mcexec_fork_sync_unlock_bridge();assert(mcexec_clone_fork_bridge()==123);assert(mcexec_clone_waitpid_nohang_bridge(123)==123);mcexec_clone_sched_yield_bridge();clear_all();
 puts("clone-child-fixture-complete");return 0;
}
