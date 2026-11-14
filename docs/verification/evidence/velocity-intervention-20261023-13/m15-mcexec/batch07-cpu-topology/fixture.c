/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Deterministic topology/affinity providers; no real binding or device mutation.
 */
#include "fixture-prelude.h"
int fd=77,ncpu,nnodes,debug;void *numa_nodes;size_t cpu_set_size;
cpu_set_t mcexec_partition_cpu_set_storage;
static int env_on,env_calls,request_ret,stat_ret;
static struct program_load_desc desc;
static int core,rank,linux_node,mapped;
char *__wrap_getenv(const char *n) {assert(!strcmp(n,"FLIB_AFFINITY_ON_PROCESS"));env_calls++;puts("get-affinity-env");return env_on?"2,3":NULL;}
pid_t __wrap_getppid(void) {return 999;}
int __wrap_stat(const char *p,struct stat *out) {assert(!strcmp(p,"/sys/class/mcos/mcos0/sys/devices/system/node/node2/cpu65"));printf("node-stat=%d\n",stat_ret);return stat_ret;}
int __wrap_ioctl(int f,unsigned long cmd,...) {
 assert(f==77);if(cmd==MCEXEC_UP_GET_CPU){puts("get-cpu");return 128;}if(cmd==MCEXEC_UP_GET_NODES){puts("get-nodes");return 3;}
 assert(cmd==MCEXEC_UP_GET_CPUSET);va_list ap;va_start(ap,cmd);struct get_cpu_set_arg *a=va_arg(ap,void*);va_end(ap);
 assert(a->nr_processes==4&&a->ppid==999&&a->cpu_set==desc.cpu_set&&a->cpu_set_size==sizeof(desc.cpu_set)&&a->target_core==&core&&a->process_rank==&rank&&a->mcexec_linux_numa==&linux_node&&a->ikc_mapped==&mapped&&a->mcexec_cpu_set==&mcexec_partition_cpu_set_storage&&a->mcexec_cpu_set_size==sizeof(cpu_set_t));
 if(env_on)assert(a->req_cpu_list&&!strcmp(a->req_cpu_list,"2,3")&&a->req_cpu_list_len==4);else assert(!a->req_cpu_list&&!a->req_cpu_list_len);
 for(size_t i=0;i<sizeof(cpu_set_t);i++)assert(!((unsigned char*)a->mcexec_cpu_set)[i]);
 *(unsigned long*)a->cpu_set=0x55;*(unsigned long*)a->mcexec_cpu_set=0xaa;*a->target_core=7;*a->process_rank=3;*a->mcexec_linux_numa=2;*a->ikc_mapped=1;
 printf("get-cpuset=%d,%d\n",env_on,request_ret);errno=EINVAL;return request_ret;
}
int __wrap_sched_setaffinity(pid_t pid,size_t size,const cpu_set_t *set) {assert(!pid&&size==sizeof(cpu_set_t)&&set==&mcexec_partition_cpu_set_storage&&*(unsigned long*)set==0xaa);puts("sched-affinity-provider");return -1;}
int numa_run_on_node(int node) {assert(node==2);puts("numa-run-provider");return -5;}
void __wrap_perror(const char *s) {assert(!strcmp(s,"getting CPU set for partitioned execution"));printf("perror-provider=%d\n",errno);}
int __wrap_close(int f) {assert(f==77);puts("close-provider");return 0;}
int main(void) {
size_t abi[]={sizeof(struct stat),_Alignof(struct stat),sizeof(cpu_set_t),_Alignof(cpu_set_t),sizeof(struct get_cpu_set_arg),_Alignof(struct get_cpu_set_arg),offsetof(struct get_cpu_set_arg,nr_processes),offsetof(struct get_cpu_set_arg,req_cpu_list),offsetof(struct get_cpu_set_arg,req_cpu_list_len),offsetof(struct get_cpu_set_arg,process_rank),offsetof(struct get_cpu_set_arg,ppid),offsetof(struct get_cpu_set_arg,cpu_set),offsetof(struct get_cpu_set_arg,cpu_set_size),offsetof(struct get_cpu_set_arg,target_core),offsetof(struct get_cpu_set_arg,mcexec_linux_numa),offsetof(struct get_cpu_set_arg,mcexec_cpu_set),offsetof(struct get_cpu_set_arg,mcexec_cpu_set_size),offsetof(struct get_cpu_set_arg,ikc_mapped)};
#ifdef RUST_IMPL
 extern size_t mcexec_topology_fixture_abi(size_t*);size_t rustabi[30];size_t count=mcexec_topology_fixture_abi(rustabi);assert(count==sizeof(abi)/sizeof(*abi)&&!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(size_t i=0;i<sizeof(abi)/sizeof(*abi);i++)printf("%zu,",abi[i]);puts("");
 int counts[]={0,1,63,64,65,1024};for(int i=0;i<6;i++){size_t n=mcexec_main_cpu_alloc_size_bridge(counts[i]);assert(n==CPU_ALLOC_SIZE(counts[i]));printf("alloc-size=%d,%zu\n",counts[i],n);}
 unsigned long sets[6];memset(sets,0xa5,sizeof sets);mcexec_main_publish_topology_bridge(128,3,16,sets);assert(ncpu==128&&nnodes==3&&cpu_set_size==16&&numa_nodes==sets);
 mcexec_main_numa_node_zero_bridge(sets,16,1);assert(sets[0]==0xa5a5a5a5a5a5a5a5UL&&!sets[2]&&!sets[3]&&sets[4]==0xa5a5a5a5a5a5a5a5UL);
 mcexec_main_numa_node_set_cpu_bridge(sets,16,1,0);mcexec_main_numa_node_set_cpu_bridge(sets,16,1,65);mcexec_main_numa_node_set_cpu_bridge(sets,16,1,128);mcexec_main_numa_node_set_cpu_bridge(sets,16,1,-1);assert(sets[2]==1&&sets[3]==2);
 assert(mcexec_numa_node_cpu_isset_bridge(1,0)==1&&mcexec_numa_node_cpu_isset_bridge(1,65)==1&&!mcexec_numa_node_cpu_isset_bridge(1,64)&&!mcexec_numa_node_cpu_isset_bridge(1,128));
 assert(mcexec_overlay_cpu_in_node_bridge(65,1)==1&&!mcexec_overlay_cpu_in_node_bridge(-1,1)&&!mcexec_overlay_cpu_in_node_bridge(128,1)&&!mcexec_overlay_cpu_in_node_bridge(1,-1)&&!mcexec_overlay_cpu_in_node_bridge(1,3));puts("cpuset-macros-complete");
 assert(mcexec_main_get_cpu_bridge()==128&&mcexec_main_get_nodes_bridge()==3);
 stat_ret=0;assert(mcexec_main_node_cpu_exists_bridge(2,65)==1);stat_ret=-1;assert(!mcexec_main_node_cpu_exists_bridge(2,65));
 for(env_on=0;env_on<2;env_on++){env_calls=0;request_ret=env_on?-1:0;debug=env_on;memset(&mcexec_partition_cpu_set_storage,0xff,sizeof(cpu_set_t));assert(mcexec_partition_get_cpuset_bridge(&desc,4,&core,&rank,&linux_node,&mapped)==request_ret);assert(core==7&&rank==3&&linux_node==2&&mapped==1&&env_calls==(env_on?2:1)&&desc.cpu_set[0]==0x55);assert(mcexec_partition_sched_setaffinity_bridge()==-1);}
 assert(numa_nodes==sets&&mcexec_partition_numa_run_bridge(2)==-5);mcexec_partition_get_cpuset_failed_bridge();
 mcexec_main_no_cpu_bridge();mcexec_main_no_numa_node_bridge();mcexec_main_alloc_nodes_error_bridge();mcexec_numa_local_cpu_log_bridge(65);mcexec_numa_node_cpu_log_bridge(65,1);mcexec_process_thread_plan_flib_log_bridge(4);mcexec_partition_rank_log_bridge(3,7);mcexec_partition_sched_setaffinity_warning_bridge();mcexec_partition_numa_run_warning_bridge(2);
 puts("topology-fixture-complete");return 0;
}
