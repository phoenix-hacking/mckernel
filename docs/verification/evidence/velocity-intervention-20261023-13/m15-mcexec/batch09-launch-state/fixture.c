/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * All reexec/personality/rlimit/process effects are deterministic providers.
 */
#include "fixture-prelude.h"
#include "fixture-globals.inc"
#ifdef USE_SYSCALL_MOD_CALL
int __glob_argc;char **__glob_argv;
#endif
static int persona_mode,persona_calls,in_persona,marker,get_fail,freed;
static char *args[]={"mcexec","app",NULL};
void *__real_malloc(size_t);void __real_free(void*);
void __wrap_free(void *p) {freed++;puts("free-owned-path");__real_free(p);}
long __wrap_sysconf(int key) {assert(key==_SC_PAGESIZE);puts("sysconf-pagesize");return 4096;}
int __wrap_getrlimit(__rlimit_resource_t r,struct rlimit *out) {assert(r==RLIMIT_STACK);puts("get-stack-limit");if(get_fail)return -1;out->rlim_cur=128;out->rlim_max=256;return 0;}
int __wrap_setrlimit(__rlimit_resource_t r,const struct rlimit *v) {assert(r==RLIMIT_STACK&&v->rlim_cur==10&&v->rlim_max==20);puts("set-stack-limit");return 31;}
int __wrap_personality(unsigned long value) {persona_calls++;printf("personality-provider=%lx\n",value);errno=EACCES;if(persona_calls==1)return persona_mode==0||persona_mode==7?ADDR_NO_RANDOMIZE:persona_mode==8?(ADDR_NO_RANDOMIZE|READ_IMPLIES_EXEC):0;if(persona_mode==2)return -1;return value;}
char *__wrap_getenv(const char *n) {if(!strcmp(n,"MCEXEC_ADDR_NO_RANDOMIZE")){printf("get-persona-env=%d\n",marker);return marker?"1":NULL;}assert(!strcmp(n,"NAME"));puts("get-loader-env");return "present";}
int __wrap_setenv(const char *n,const char *v,int overwrite) {printf("set-env=%s,%s,%d\n",n,v,overwrite);if(!strcmp(n,"MCEXEC_ADDR_NO_RANDOMIZE")){assert(!strcmp(v,"1")&&overwrite==1);if(persona_mode==3)return -1;marker=1;return 0;}if(!strcmp(n,"MCKERNEL_RLIMIT_STACK")){assert(!overwrite&&!strcmp(v,"10,20"));return 21;}assert(!strcmp(n,"LD_PRELOAD")&&!strcmp(v,"loader")&&overwrite==1);return 22;}
int __wrap_unsetenv(const char *n) {printf("unset-env=%s\n",n);if(!strcmp(n,"MCEXEC_ADDR_NO_RANDOMIZE")){if(persona_mode==7)return -1;marker=0;return 0;}assert(!strcmp(n,"MCKERNEL_LD_PRELOAD"));return 23;}
ssize_t __wrap_readlink(const char *p,char *out,size_t n) {assert(!strcmp(p,"/proc/self/exe"));printf("read-self=%zu\n",n);errno=EIO;if(in_persona&&persona_mode==4)return -1;if(in_persona&&persona_mode==5)return n;assert(n>=5);memcpy(out,"self",5);return 4;}
int __wrap_execv(const char *p,char *const *argv) {assert(argv==args);printf("exec-provider=%s\n",p);errno=ENOENT;return in_persona?(persona_mode==6?0:-1):41;}
int __wrap_getopt_long(int argc,char *const *argv,const char *shorts,const struct option *options,int *index) {assert(argc==2&&argv==args&&!strcmp(shorts,"+c:n:t:M:h:e:s:m:u:S:f:")&&options==mcexec_options&&!index);puts("getopt-provider");return 'x';}
int __wrap_pthread_spin_init(pthread_spinlock_t *p,int shared) {assert(p==&overlay_fd_lock&&!shared);puts("spin-init");return 0;}
int __wrap_open(const char *p,int flags,...) {assert(!strcmp(p,"/dev/mock")&&flags==O_RDWR);puts("open-device");return 66;}
int __wrap_ioctl(int f,unsigned long req,...) {assert(f==66&&req==IHK_OS_GET_BUILDID);va_list ap;va_start(ap,req);char *p=va_arg(ap,char*);va_end(ap);strcpy(p,"id");puts("query-build-id");return 0;}
int __wrap_close(int f) {assert(f==66);puts("close-device");return 0;}
FILE *__wrap_popen(const char *cmd,const char *mode) {assert(!strcmp(cmd,"command")&&!strcmp(mode,"r"));puts("popen-provider");return (void*)0x4444;}
int __wrap_pclose(FILE *p) {assert(p==(void*)0x4444);puts("pclose-provider");return -1;}
ssize_t __wrap_getline(char **line,size_t *n,FILE *p) {assert(p==(void*)0x4444);*line="line";*n=5;puts("getline-provider");return 4;}
int __wrap_prctl(int option,...) {assert(option==PR_GET_THP_DISABLE);va_list ap;va_start(ap,option);for(int i=0;i<4;i++)assert(!va_arg(ap,int));va_end(ap);puts("prctl-provider");return -1;}
int main(void) {
size_t abi[]={sizeof(struct mcexec_main_state_ptrs),_Alignof(struct mcexec_main_state_ptrs),offsetof(struct mcexec_main_state_ptrs,nr_processes),offsetof(struct mcexec_main_state_ptrs,nr_threads),offsetof(struct mcexec_main_state_ptrs,mpol_threshold),offsetof(struct mcexec_main_state_ptrs,heap_extension),offsetof(struct mcexec_main_state_ptrs,straight_map_threshold),offsetof(struct mcexec_main_state_ptrs,stack_premap),offsetof(struct mcexec_main_state_ptrs,stack_max),offsetof(struct mcexec_main_state_ptrs,uti_thread_rank),offsetof(struct mcexec_main_state_ptrs,mcexec_flags),offsetof(struct mcexec_main_state_ptrs,mpol_bind_nodes),offsetof(struct mcexec_main_state_ptrs,enable_uti),offsetof(struct mcexec_main_state_ptrs,enable_vdso),offsetof(struct mcexec_main_state_ptrs,profile),offsetof(struct mcexec_main_state_ptrs,mpol_no_heap),offsetof(struct mcexec_main_state_ptrs,mpol_no_stack),offsetof(struct mcexec_main_state_ptrs,mpol_no_bss),offsetof(struct mcexec_main_state_ptrs,mpol_shm_premap),offsetof(struct mcexec_main_state_ptrs,no_bind_ikc_map),offsetof(struct mcexec_main_state_ptrs,straight_map),offsetof(struct mcexec_main_state_ptrs,uti_use_last_cpu),offsetof(struct mcexec_main_state_ptrs,enable_tofu),offsetof(struct mcexec_main_state_ptrs,rlim_cur),offsetof(struct mcexec_main_state_ptrs,rlim_max)};
#ifdef RUST_IMPL
 extern size_t mcexec_launch_fixture_abi(size_t*);size_t rustabi[40];size_t count=mcexec_launch_fixture_abi(rustabi);assert(count==sizeof(abi)/sizeof(*abi)&&!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(size_t i=0;i<sizeof(abi)/sizeof(*abi);i++)printf("%zu,",abi[i]);puts("");
 debug=1;assert(mcexec_main_page_size_bridge()==4096);mcexec_main_publish_page_altroot_bridge(4096,"root");assert(page_size==4096&&page_mask==~4095UL&&!strcmp(mcexec_altroot_bridge(),"root"));
 exec_path=__real_malloc(4);char *next=__real_malloc(8);mcexec_load_desc_publish_exec_path_bridge(next);assert(exec_path==next&&freed==1);__real_free(next);exec_path=NULL;
 unsigned long cur=9,max=10;get_fail=1;assert(mcexec_main_load_stack_rlimit_bridge(&cur,&max)==1&&cur==9&&max==10);get_fail=0;assert(!mcexec_main_load_stack_rlimit_bridge(&cur,&max)&&cur==128&&max==256);
 assert(mcexec_reduce_stack_setenv_bridge("10,20")==21&&mcexec_reduce_stack_setrlimit_bridge(10,20)==31);
 char path[64];assert(mcexec_reduce_stack_readlink_bridge(path,sizeof path)==4&&mcexec_find_libdir_readlink_bridge(path,sizeof path)==4);assert(mcexec_reduce_stack_execv_bridge("self",args)==41);
 assert(mcexec_execve1_rlim_cur_bridge()==128&&mcexec_execve1_rlim_max_bridge()==256&&mcexec_execve1_enable_vdso_bridge()==enable_vdso&&mcexec_execve1_stack_premap_bridge()==stack_premap);ischild=1;assert(mcexec_main_loop_is_child_bridge()==1);
 mcexec_main_publish_args_bridge(2,args);struct mcexec_main_state_ptrs state;memset(&state,0xa5,sizeof state);mcexec_main_state_ptrs_bridge(&state);assert(state.nr_processes==&nr_processes&&state.rlim_cur==&rlim_stack.rlim_cur&&state.rlim_max==&rlim_stack.rlim_max);*state.nr_processes=11;assert(nr_processes==11);
#ifndef ENABLE_TOFU
 assert(!state.enable_tofu);
#endif
 optarg="option";optind=3;assert(mcexec_main_next_option_bridge(2,args)=='x'&&!strcmp(mcexec_main_optarg_bridge(),"option")&&mcexec_main_optind_bridge()==3);
 mcexec_main_publish_mcosid_bridge(12);assert(mcexec_opendev_mcosid_bridge()==12&&mcexec_overlay_mcosid_bridge()==12);assert(mcexec_main_uti_unavailable_bridge(0)==0);
#ifndef ENABLE_UTI
 assert(mcexec_main_uti_unavailable_bridge(1)==1);
#endif
 enable_uti=3;disable_sched_yield=4;assert(mcexec_ld_preload_enable_uti_bridge()==3&&mcexec_overlay_enable_uti_bridge()==3&&mcexec_ld_preload_disable_sched_yield_bridge()==4);mcexec_main_overlay_lock_init_bridge();assert(mcexec_opendev_dev_bridge()==dev&&mcexec_opendev_dev_size_bridge()==64);assert(mcexec_opendev_open_bridge("/dev/mock")==66);mcexec_opendev_publish_fd_bridge(66);assert(fd==66);char id[8];assert(!mcexec_opendev_query_buildid_bridge(66,id)&&!strcmp(id,"id"));mcexec_opendev_close_bridge(66);
 void *file=mcexec_find_libdir_popen_bridge("command");char *line=NULL;size_t size=0;assert(mcexec_find_libdir_getline_bridge(&line,&size,file)==4&&size==5&&!strcmp(line,"line"));mcexec_find_libdir_pclose_bridge(file);mcexec_find_libdir_free_bridge(__real_malloc(4));
 assert(!strcmp(mcexec_ld_preload_getenv_bridge("NAME"),"present")&&mcexec_ld_preload_setenv_bridge("loader")==22&&mcexec_ld_preload_unsetenv_bridge()==23);assert(mcexec_get_thp_disable_prctl_bridge()==-1);
#ifdef ENABLE_QLMPI
 assert(mcexec_ld_preload_enable_qlmpi_bridge()==1);
#else
 assert(!mcexec_ld_preload_enable_qlmpi_bridge());
#endif
 for(persona_mode=0;persona_mode<9;persona_mode++){in_persona=1;persona_calls=0;marker=persona_mode==1||persona_mode==7;errno=EIO;printf("persona-case=%d\n",persona_mode);int rc=mcexec_main_personality_bridge(args);printf("persona-result=%d,%d,%d\n",rc,marker,persona_calls);assert(rc==((persona_mode==0||persona_mode==6||persona_mode==8)?0:1));}in_persona=0;
 puts("launch-state-fixture-complete");return 0;
}
