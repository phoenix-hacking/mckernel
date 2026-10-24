/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Optional project/platform side effects are fixture providers, not runtime credit.
 */
#include "fixture-prelude.h"
int fd=77,debug=1;cpu_set_t mcexec_partition_cpu_set_storage;
static int cmd_fail,unshare_rc,mount_fail,ioctl_calls;
static char *argv[]={"mcexec","app",NULL};
int mcexec_main_body(int argc,char **args) {assert(argc==2&&args==argv);puts("rust-main-body-provider");return 43;}
int mc_cmd_server_init(void) {puts("cmd-main-init");return cmd_fail==1;}
void mc_cmd_server_exit(void) {puts("cmd-main-exit");}
int ibmic_cmd_server_init(void) {puts("cmd-dcfa-init");return cmd_fail==2;}
void ibmic_cmd_server_exit(void) {puts("cmd-dcfa-exit");}
int dcfampi_cmd_server_init(void) {puts("cmd-dcfampi-init");return cmd_fail==3;}
void dcfampi_cmd_server_exit(void) {puts("cmd-dcfampi-exit");}
int isunshare(void) {printf("isunshare-provider=%d\n",unshare_rc);return unshare_rc;}
int __wrap_ioctl(int f,unsigned long cmd,...) {
 assert(f==77);ioctl_calls++;va_list ap;va_start(ap,cmd);void *raw=va_arg(ap,void*);va_end(ap);
 if(cmd==MCEXEC_UP_SYS_UNSHARE){struct sys_unshare_desc *d=raw;assert(d->unshare_flags==CLONE_NEWNS);puts("unshare-ioctl");}
 else {assert(cmd==MCEXEC_UP_SYS_MOUNT);struct sys_mount_desc *d=raw;assert(!d->dev_name&&!strcmp(d->dir_name,"/")&&!d->type&&d->flags==(MS_PRIVATE|MS_REC)&&!d->data);puts("mount-ioctl");}
 errno=EACCES;return mount_fail==ioctl_calls?-1:0;
}
int numa_num_possible_cpus(void) {return 4;}
pid_t __wrap_getpid(void) {return 123;}
int __wrap_sched_getaffinity(pid_t p,size_t n,cpu_set_t *set) {assert(p==0&&n==sizeof(cpu_set_t));CPU_ZERO(set);CPU_SET(0,set);CPU_SET(2,set);CPU_SET(511,set);puts("get-affinity-provider");return 0;}
int main(void) {
 size_t abi[]={sizeof(struct sys_unshare_desc),_Alignof(struct sys_unshare_desc),sizeof(struct sys_mount_desc),_Alignof(struct sys_mount_desc),offsetof(struct sys_mount_desc,dev_name),offsetof(struct sys_mount_desc,dir_name),offsetof(struct sys_mount_desc,type),offsetof(struct sys_mount_desc,flags),offsetof(struct sys_mount_desc,data)};
#ifdef RUST_IMPL
 extern void mcexec_entry_fixture_abi(size_t*);size_t rustabi[9];mcexec_entry_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<9;i++)printf("%zu,",abi[i]);puts("");
 assert(mcexec_main_entry_fixture(2,argv)==43);assert(mcexec_opendev_buildid_size_bridge()==sizeof(BUILDID)&&!strcmp(mcexec_opendev_buildid_bridge(),BUILDID));char *result=mcexec_opendev_query_result_bridge();for(size_t i=0;i<sizeof(BUILDID);i++)assert(!result[i]);memset(result,0x7f,sizeof(BUILDID));assert(mcexec_opendev_query_result_bridge()==result);for(size_t i=0;i<sizeof(BUILDID);i++)assert(!result[i]);printf("buildid=%s,%zu\n",mcexec_opendev_buildid_bridge(),mcexec_opendev_buildid_size_bridge());
 for(cmd_fail=0;cmd_fail<4;cmd_fail++){int rc=mcexec_main_cmd_servers_init_bridge();printf("cmd-result=%d\n",rc);
#ifdef USE_SYSCALL_MOD_CALL
 int expected=cmd_fail==1?1:0;
#ifdef CMD_DCFA
 if(cmd_fail==2)expected=-1;
#endif
#ifdef CMD_DCFAMPI
 if(cmd_fail==3)expected=-1;
#endif
 assert(rc==expected);
#else
 assert(!rc);
#endif
 }
 mcexec_exit_cmd_servers_bridge();
 int rc[]={0,0,-1,1};int fail[]={0,1,0,0};for(int i=0;i<4;i++){unshare_rc=rc[i];mount_fail=fail[i];ioctl_calls=0;int ret=mcexec_main_bind_mount_bridge();printf("mount-result=%d,%d\n",ret,ioctl_calls);
#ifdef MCEXEC_BIND_MOUNT
 assert(ret==((unshare_rc==-1||mount_fail)?1:0));
#else
 assert(!ret&&!ioctl_calls);
#endif
 }
 CPU_ZERO(&mcexec_partition_cpu_set_storage);CPU_SET(1,&mcexec_partition_cpu_set_storage);CPU_SET(3,&mcexec_partition_cpu_set_storage);mcexec_partition_debug_ikc_binding_bridge();mcexec_partition_debug_numa_binding_bridge();
 puts("entry-metadata-options-fixture-complete");return 0;
}
