/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * All pthread lifecycle effects use deterministic wrapper providers, no threads/signals.
 */
#include "fixture-prelude.h"
struct thread_data_s *thread_data;
pthread_mutex_t lock;
pthread_barrier_t init_ready,uti_init_ready;
int n_threads;
static int alloc_fail,create_count,create_fail_at,wait_count,join_count;
void *__real_malloc(size_t);
void *__wrap_malloc(size_t n) { if(alloc_fail) {alloc_fail=0;return NULL;} return __real_malloc(n); }
void *mcexec_main_loop_thread_func_body(void *p) { assert(0);return p; }
static int which(void *p) { return p==&init_ready?1:p==&uti_init_ready?2:3; }
int __wrap_pthread_mutex_init(pthread_mutex_t *p,const pthread_mutexattr_t *a) { assert(p==&lock&&!a);puts("mutex-init");return 0; }
int __wrap_pthread_barrier_init(pthread_barrier_t *p,const pthread_barrierattr_t *a,unsigned n) { assert(!a);printf("barrier-init=%d,%u\n",which(p),n);return 0; }
int __wrap_pthread_barrier_wait(pthread_barrier_t *p) { wait_count++;printf("barrier-wait=%d\n",which(p));return PTHREAD_BARRIER_SERIAL_THREAD; }
int __wrap_pthread_create(pthread_t *id,const pthread_attr_t *a,void *(*entry)(void *),void *p) {
 struct thread_data_s *t=p;assert(!a&&entry==mcexec_main_loop_thread_func_body&&t==thread_data);
 assert(!t->ret&&!t->tid&&!t->terminate&&!t->remote_tid&&!t->remote_cpu&&!t->joined&&!t->detached&&t->lock==&lock);
 create_count++;int fail=create_count==create_fail_at;
 if(!fail)*id=(pthread_t)(100+create_count);
 printf("create=%d,%d,%d,%d\n",create_count,t->cpu,which(t->init_ready),fail);
 return fail?EAGAIN:0;
}
int __wrap_pthread_join(pthread_t id,void **p) { assert(!p);join_count++;printf("join=%lu\n",(unsigned long)id);return ESRCH; }
int __wrap_pthread_kill(pthread_t id,int sig) { printf("kill-provider=%lu,%d\n",(unsigned long)id,sig);return ESRCH; }
static void clear_nodes(void) { while(thread_data) {struct thread_data_s *t=thread_data;thread_data=t->next;free(t);} }
int main(void) {
 size_t abi[]={sizeof(struct thread_data_s),_Alignof(struct thread_data_s),offsetof(struct thread_data_s,thread_id),offsetof(struct thread_data_s,cpu),offsetof(struct thread_data_s,lock),offsetof(struct thread_data_s,init_ready)};
#ifdef RUST_IMPL
 extern void mcexec_worker_fixture_abi(size_t *);size_t rustabi[6];mcexec_worker_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<6;i++)printf("%zu,",abi[i]);puts("");
 struct thread_data_s *out=(void*)1;
 alloc_fail=1;assert(mcexec_create_worker_thread_body(&out,&init_ready)==ENOMEM);assert(out==(void*)1&&!thread_data);puts("alloc-failure-preserved");
 mcexec_init_worker_threads_reset_cpuid_bridge();
 assert(!mcexec_create_worker_thread_body(&out,&init_ready));assert(out==thread_data&&out->cpu==0);
 struct thread_data_s *first=out;
 assert(!mcexec_create_worker_thread_body(NULL,NULL));assert(thread_data->next==first&&thread_data->cpu==1);
 create_fail_at=3;assert(mcexec_create_worker_thread_body(&out,&uti_init_ready)==EAGAIN);assert(out==thread_data&&out->cpu==2&&!out->thread_id);puts("create-failure-published");
 out->detached=1;first->joined=1;mcexec_join_all_threads_body();assert(join_count==1&&thread_data->next->joined);mcexec_join_all_threads_body();assert(join_count==1);
 assert(mcexec_kill_thread_pthread_kill_bridge(first,SIGURG)==ESRCH);
 clear_nodes();create_count=0;create_fail_at=0;wait_count=0;join_count=0;n_threads=2;
 assert(!init_worker_threads(99));assert(create_count==3&&wait_count==1);mcexec_join_all_threads_body();assert(join_count==3);clear_nodes();
 create_count=0;create_fail_at=2;wait_count=0;n_threads=4;
 assert(init_worker_threads(99)==-EAGAIN);assert(create_count==2&&!wait_count&&thread_data&&thread_data->next);clear_nodes();
 create_count=0;create_fail_at=0;mcexec_util_thread_barrier_init_bridge();assert(!mcexec_util_thread_create_worker_bridge(&out));assert(out==thread_data&&out->init_ready==&uti_init_ready);
 mcexec_util_thread_barrier_wait_bridge();assert(mcexec_main_loop_thread_barrier_wait_bridge(&uti_init_ready)==PTHREAD_BARRIER_SERIAL_THREAD);clear_nodes();
 puts("worker-lifecycle-fixture-complete");return 0;
}
