/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Deterministic providers; no real map/lock/ioctl/exit/thread/switch effects.
 */
#include "fixture-prelude.h"
int fd=55,debug=1;static int stat_rc,symlink_mode;static jmp_buf frame;
static char text[]="text";static char *args[]={"mcexec",NULL};
int __wrap_stat(const char *path,struct stat *sb) {assert(!strcmp(path,"path"));memset(sb,0,sizeof(*sb));sb->st_size=123;sb->st_mode=symlink_mode?S_IFLNK:S_IFREG;errno=EACCES;printf("stat-provider=%d\n",stat_rc);return stat_rc;}
int __wrap_lstat(const char *path,struct stat *sb) {assert(!strcmp(path,"path"));memset(sb,0,sizeof(*sb));sb->st_size=123;sb->st_mode=symlink_mode?S_IFLNK:S_IFREG;errno=EACCES;printf("lstat-provider=%d\n",stat_rc);return stat_rc;}
ssize_t __wrap_readlink(const char *path,char *out,size_t n) {assert(!strcmp(path,"path")&&n==8);memcpy(out,"target",7);puts("readlink-provider");return -1;}
ssize_t mcexec_find_libdir_body(char *out,size_t n) {assert(n==8);memcpy(out,"libdir",7);puts("find-libdir-provider");return 0x100000004L;}
void *__wrap_mmap(void *p,size_t n,int prot,int flags,int f,off_t off) {assert(!p&&n==4096&&prot==3&&flags==(MAP_PRIVATE|MAP_ANONYMOUS)&&f==-1&&!off);puts("mmap-provider");return (void*)0x8888;}
int __wrap_mlock(const void *p,size_t n) {assert((p==(void*)0x8888&&n==4096)||(p==text&&n==4));puts("mlock-provider");return -1;}
int __wrap_ioctl(int f,unsigned long request,...) {assert(f==55&&request==MCEXEC_UP_CREATE_PPD);va_list ap;va_start(ap,request);void *p=va_arg(ap,void*);va_end(ap);assert(!p);puts("create-ppd-provider");return -1;}
void __wrap_perror(const char *message) {printf("perror-provider=%s,%d\n",message,errno);}
int __wrap_close(int f) {assert(f==55);puts("close-provider");return -1;}
void __wrap_exit(int code) {assert(code==1);puts("exit-provider=1");longjmp(frame,1);}
void print_usage(char **argv) {assert(argv==args);puts("usage-provider");}
void mcexec_kill_thread_body(unsigned long tid,unsigned long sig,void *thread) {assert(tid==12&&sig==13&&thread==(void*)0x1111);puts("kill-thread-forward");}
long mcexec_util_thread_body(struct thread_data_s *thread,unsigned long rp,int tid,unsigned long attr,unsigned long info,unsigned long desc) {assert(thread==(void*)0x1111&&rp==1&&tid==2&&attr==3&&info==4&&desc==5);puts("util-thread-forward");return -19;}
int switch_ctx(int f,unsigned long cmd,struct uti_switch_ctx_desc *d,void *lctx,void *rctx) {assert(f==55&&cmd==MCEXEC_UP_UTI_SWITCH_CTX&&d==(void*)0x2222&&lctx==(void*)0x3333&&rctx==(void*)0x4444);puts("switch-asm-forward");return -17;}
int __wrap_printf(const char *fmt,...) {
 va_list ap;va_start(ap,fmt);int rc;
 if(!strcmp(fmt,"linux mlock(%p, %ld)\n")){void *p=va_arg(ap,void*);long n=va_arg(ap,long);assert(p==text&&n==4);rc=fprintf(stdout,"linux mlock(TEXT, %ld)\n",n);}
 else if(!strcmp(fmt,"str(%p)=%s")){void *p=va_arg(ap,void*);char *s=va_arg(ap,char*);assert(p==text&&s==text);rc=fprintf(stdout,"str(TEXT)=%s",s);}
 else rc=vfprintf(stdout,fmt,ap);va_end(ap);return rc;
}
int main(void) {
 size_t abi[]={sizeof(struct stat),_Alignof(struct stat),offsetof(struct stat,st_mode),offsetof(struct stat,st_size)};
#ifdef RUST_IMPL
 extern void mcexec_residual_fixture_abi(size_t*);size_t rustabi[4];mcexec_residual_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=%zu,%zu,%zu,%zu\n",abi[0],abi[1],abi[2],abi[3]);
 int results[]={-1,-2,0,1};for(int i=0;i<4;i++){stat_rc=results[i];long size=999;int expected=stat_rc==-1?EACCES:0;assert(mcexec_lookup_lstat_errno_bridge("path")==expected);assert(mcexec_load_desc_stat_size_bridge("path",&size)==expected&&size==(stat_rc==-1?999:123));assert(mcexec_overlay_stat_exists_bridge("path")== (stat_rc<0?-EACCES:0));assert(mcexec_overlay_stat_errno_bridge("path")==expected);for(symlink_mode=0;symlink_mode<2;symlink_mode++){int link=9;int rc=mcexec_overlay_lstat_is_symlink_bridge("path",&link);assert(rc==(stat_rc==-1?-EACCES:0)&&link==(stat_rc==-1?9:symlink_mode));}}
 char out[8];assert(mcexec_overlay_readlink_bridge("path",out,8)==-1&&!strcmp(out,"target"));assert(mcexec_overlay_find_libdir_bridge(out,8)==4&&!strcmp(out,"libdir"));
 assert(mcexec_dma_mmap_bridge()==(void*)0x8888&&mcexec_dma_mlock_bridge((void*)0x8888)==-1&&mcexec_create_ppd_bridge()==-1);assert(mcexec_debug_mlock_bridge((unsigned long)text,4)==-1);mcexec_debug_mlock_log_bridge((unsigned long)text,4);
 void (*fatal[])(void)={mcexec_dma_mmap_failed_bridge,mcexec_dma_mlock_failed_bridge,mcexec_create_ppd_failed_bridge,mcexec_flib_affinity_alloc_failed_bridge};for(int i=0;i<4;i++){errno=EIO;int escaped=setjmp(frame);if(!escaped)fatal[i]();assert(escaped==1);}
 int opts[]={'c','n','t','z'};for(int i=0;i<4;i++){int escaped=setjmp(frame);if(!escaped)mcexec_main_invalid_option_bridge(opts[i],args);assert(escaped==1);}
 errno=EIO;mcexec_main_prepare_image_failed_bridge();errno=EIO;mcexec_main_start_image_failed_bridge();mcexec_main_worker_threads_failed_bridge(-EAGAIN);mcexec_atobytes_set_errno_bridge(ERANGE);assert(errno==ERANGE);assert(mcexec_print_usage_add_envs_bridge()==1);mcexec_print_usage_write_bridge("text-ignored",4);
 mcexec_kill_thread_bridge(12,13,(void*)0x1111);assert(mcexec_sched_setaffinity_util_bridge((void*)0x1111,1,2,3,4,5)==-19);assert(mcexec_util_thread_switch_ctx_bridge((void*)0x2222,(void*)0x3333,(void*)0x4444)==-17);
 struct program_load_desc d={0};d.mpol_mode=3;d.mpol_nodemask[0]=7;mcexec_desc_mpol_log_bridge(&d);mcexec_reduce_stack_newval_overflow_bridge();mcexec_reduce_stack_setenv_failed_bridge();mcexec_main_stack_parse_failed_bridge(4);mcexec_load_realloc_failed_bridge(0x1000);
 for(debug=0;debug<2;debug++){mcexec_load_desc_sections_bridge(2);mcexec_print_desc_intro_bridge((void*)0x1234);mcexec_print_desc_main_bridge(1,2,3,4);mcexec_print_desc_section_bridge(1,2,3,4);mcexec_overlay_getdents_upper_bridge(1,2,3);mcexec_overlay_getdents_lower_bridge(1,2,3);mcexec_overlay_getdents_mck_size_log_bridge(1,2,3,4);mcexec_overlay_getdents_linux_size_log_bridge(1,2,3,4);}
 puts("residual-functional-fixture-complete");return 0;
}
