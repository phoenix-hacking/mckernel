/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "fixture-prelude.h"
static pthread_mutex_t expected_mutex=PTHREAD_MUTEX_INITIALIZER;
static void zero_bytes(const void *p,size_t n) {for(size_t i=0;i<n;i++)assert(!((const unsigned char*)p)[i]);}
int main(void) {
 size_t abi[]={sizeof(pthread_mutex_t),_Alignof(pthread_mutex_t),sizeof(pthread_barrier_t),_Alignof(pthread_barrier_t),sizeof(pthread_spinlock_t),_Alignof(pthread_spinlock_t),sizeof(struct list_head),_Alignof(struct list_head),sizeof(struct option),_Alignof(struct option),offsetof(struct option,name),offsetof(struct option,has_arg),offsetof(struct option,flag),offsetof(struct option,val),sizeof(struct rlimit),_Alignof(struct rlimit)};
#ifdef RUST_IMPL
 extern void mcexec_data_fixture_abi(size_t*);size_t rustabi[16];mcexec_data_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<16;i++)printf("%zu,",abi[i]);puts("");
 assert(!fd&&!mcosid&&!ischild&&enable_vdso==1&&!mpol_no_heap&&!mpol_no_stack&&!mpol_no_bss&&!mpol_shm_premap&&!no_bind_ikc_map&&!straight_map&&!profile&&!disable_sched_yield&&!uti_thread_rank&&!uti_use_last_cpu&&!enable_uti&&!nr_processes&&nr_threads==-1&&!master_tid&&!ncpu&&!nnodes&&!n_threads&&!page_size&&!page_mask&&!mpol_threshold&&!mcexec_flags&&straight_map_threshold==1024UL*1024&&heap_extension==~0UL&&stack_premap==2L*1024*1024&&stack_max==-1);
 assert(!exec_path&&!altroot&&!mpol_bind_nodes&&!dma_buf&&!thread_data&&!fork_sync_top&&!numa_nodes&&!cpu_set_size&&!rlim_stack.rlim_cur&&!rlim_stack.rlim_max);
#ifdef DEBUG
 assert(debug==1);
#else
 assert(debug==0);
#endif
#ifdef ENABLE_TOFU
 assert(!enable_tofu);
#endif
 zero_bytes(dev,64);zero_bytes(&mcexec_partition_cpu_set_storage,sizeof(cpu_set_t));zero_bytes(&init_ready,sizeof(init_ready));zero_bytes(&uti_init_ready,sizeof(uti_init_ready));assert(overlay_fd_list.next==&overlay_fd_list&&overlay_fd_list.prev==&overlay_fd_list);
 assert(!memcmp(&lock,&expected_mutex,sizeof(lock))&&!memcmp(&fork_sync_mutex,&expected_mutex,sizeof(lock)));puts("all-original-initial-values-match");
 int index=0;
 assert(!strcmp(mcexec_options[index].name,"disable-vdso")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&enable_vdso&&mcexec_options[index].val==0);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"enable-vdso")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&enable_vdso&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"profile")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&profile&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"mpol-no-heap")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&mpol_no_heap&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"mpol-no-stack")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&mpol_no_stack&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"mpol-no-bss")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&mpol_no_bss&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"mpol-shm-premap")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&mpol_shm_premap&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"no-bind-ikc-map")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&no_bind_ikc_map&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"mpol-threshold")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='M');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"enable-straight-map")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&straight_map&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"straight-map-threshold")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='S');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"disable-sched-yield")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&disable_sched_yield&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"extend-heap-by")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='h');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"stack-premap")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='s');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"uti-thread-rank")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='u');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"uti-use-last-cpu")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&uti_use_last_cpu&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"enable-uti")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&enable_uti&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
#ifdef ENABLE_TOFU
 assert(!strcmp(mcexec_options[index].name,"enable-tofu")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&enable_tofu&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
#endif
 assert(!strcmp(mcexec_options[index].name,"debug-mcexec")&&mcexec_options[index].has_arg==no_argument&&mcexec_options[index].flag==&debug&&mcexec_options[index].val==1);printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;
 assert(!strcmp(mcexec_options[index].name,"flags")&&mcexec_options[index].has_arg==required_argument&&mcexec_options[index].flag==NULL&&mcexec_options[index].val=='f');printf("option=%d,%s,%d,%d\n",index,mcexec_options[index].name,mcexec_options[index].has_arg,mcexec_options[index].val);index++;

 assert(!mcexec_options[index].name&&!mcexec_options[index].has_arg&&!mcexec_options[index].flag&&!mcexec_options[index].val);
 char *args[]={"mcexec","--disable-vdso","--profile","--mpol-threshold=1234","--flags=ff","--debug-mcexec",NULL};optind=0;int expected[]={0,0,'M','f',0};for(int i=0;i<5;i++){int rc=getopt_long(6,args,"+c:n:t:M:h:e:s:m:u:S:f:",mcexec_options,NULL);assert(rc==expected[i]);printf("getopt=%d,%s\n",rc,optarg?optarg:"NULL");}assert(getopt_long(6,args,"+c:n:t:M:h:e:s:m:u:S:f:",mcexec_options,NULL)==-1&&!enable_vdso&&profile==1&&debug==1);
 pthread_mutex_t *mutexes[]={&lock,&fork_sync_mutex};for(int i=0;i<2;i++){assert(!pthread_mutex_trylock(mutexes[i]));assert(!pthread_mutex_unlock(mutexes[i]));assert(!pthread_mutex_destroy(mutexes[i]));puts("real-platform-mutex-ok");}
 pthread_barrier_t *barriers[]={&init_ready,&uti_init_ready};for(int i=0;i<2;i++){assert(!pthread_barrier_init(barriers[i],NULL,1));assert(pthread_barrier_wait(barriers[i])==PTHREAD_BARRIER_SERIAL_THREAD);assert(!pthread_barrier_destroy(barriers[i]));puts("real-platform-barrier-ok");}
 assert(!pthread_spin_init(&overlay_fd_lock,0)&&!pthread_spin_lock(&overlay_fd_lock)&&!pthread_spin_unlock(&overlay_fd_lock)&&!pthread_spin_destroy(&overlay_fd_lock));puts("real-platform-spinlock-ok");puts("runtime-data-fixture-complete");return 0;
}
