/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Deterministic libc providers; no files, credentials or syscalls changed.
 */
#include "fixture-prelude.h"
int debug;static long provider_ret;
static long result(void) {errno=EACCES;return provider_ret;}
ssize_t __wrap_readlinkat(int fd,const char *p,char *b,size_t n) {assert(fd==-100&&!strcmp(p,"path")&&!strcmp(b,"buf")&&n==64);puts("provider-readlinkat");return result();}
ssize_t __wrap_readlink(const char *p,char *b,size_t n) {assert(!strcmp(p,"path")&&!strcmp(b,"buf")&&n==64);puts("provider-readlink");return result();}
int __wrap_fstatat(int fd,const char *p,struct stat *b,int f) {assert(fd==-100&&!strcmp(p,"path")&&b==(void*)0x9999&&f==0x100);puts("provider-fstatat");return result();}
int __wrap_stat(const char *p,struct stat *b) {assert(!strcmp(p,"path")&&b==(void*)0x9999);puts("provider-stat");return result();}
int __wrap_faccessat(int fd,const char *p,int m,int f) {assert(fd==-100&&!strcmp(p,"path")&&m==7&&f==0x100);puts("provider-faccessat");return result();}
int __wrap_access(const char *p,int m) {assert(!strcmp(p,"path")&&m==7);puts("provider-access");return result();}
ssize_t __wrap_getxattr(const char *p,const char *name,void *v,size_t n) {assert(!strcmp(p,"path")&&!strcmp(name,"name")&&v==(void*)0x9999&&n==64);puts("provider-getxattr");return result();}
ssize_t __wrap_lgetxattr(const char *p,const char *name,void *v,size_t n) {assert(!strcmp(p,"path")&&!strcmp(name,"name")&&v==(void*)0x9999&&n==64);puts("provider-lgetxattr");return result();}
int __wrap_openat(int fd,const char *p,int flags,...) {assert(fd==-100&&!strcmp(p,"path")&&flags==65);va_list ap;va_start(ap,flags);unsigned long mode=va_arg(ap,unsigned long);va_end(ap);assert(mode==0x2000001edUL);printf("provider-openat=%lx\n",mode);return result();}
int __wrap_open(const char *p,int flags,...) {if(!strcmp(p,"/dev/null")){assert(!flags);puts("provider-perf-null");return result();}assert(!strcmp(p,"path")&&flags==65);va_list ap;va_start(ap,flags);unsigned long mode=va_arg(ap,unsigned long);va_end(ap);assert(mode==0x2000001edUL);printf("provider-open=%lx\n",mode);return result();}
int __wrap_ioctl(int fd,unsigned long request,...) {assert(fd==22&&request==MCEXEC_UP_GET_CRED);va_list ap;va_start(ap,request);unsigned long arg=va_arg(ap,unsigned long);va_end(ap);assert(arg==0x123456789abcdef0UL);puts("provider-get-cred");return result();}
int __wrap_setfsuid(uid_t a) {assert(a==1);puts("provider-setfsuid");return result();}
int __wrap_setfsgid(gid_t a) {assert(a==1);puts("provider-setfsgid");return result();}
int __wrap_setuid(uid_t a) {assert(a==1);puts("provider-setuid");return result();}
int __wrap_setgid(gid_t a) {assert(a==1);puts("provider-setgid");return result();}
int __wrap_setreuid(uid_t a,uid_t b) {assert(a==1&&b==2);puts("provider-setreuid");return result();}
int __wrap_setregid(gid_t a,gid_t b) {assert(a==1&&b==2);puts("provider-setregid");return result();}
int __wrap_setresuid(uid_t a,uid_t b,uid_t c) {assert(a==1&&b==2&&c==3);puts("provider-setresuid");return result();}
int __wrap_setresgid(gid_t a,gid_t b,gid_t c) {assert(a==1&&b==2&&c==3);puts("provider-setresgid");return result();}
long __wrap_syscall(long nr,...) {assert(nr==999);va_list ap;va_start(ap,nr);for(unsigned long i=1;i<=6;i++)assert(va_arg(ap,unsigned long)==(0x100000000UL+i));va_end(ap);puts("provider-syscall-six-args");return result();}
int __wrap_clock_gettime(clockid_t clock,struct timespec *tv) {assert(clock==7);tv->tv_sec=123;tv->tv_nsec=456;puts("provider-clock");return result();}
int main(void) {
 char buf[64]="buf";unsigned long a=0x100000001UL,b=0x200000002UL,c=0x300000003UL;
 struct syscall_wait_desc w={0};w.sr.number=999;for(int i=0;i<6;i++)w.sr.args[i]=0x100000001UL+i;
 for(int mode=0;mode<3;mode++) {provider_ret=mode==0?-1:mode==1?0:7;debug=mode==2;long expected=provider_ret==-1?-EACCES:provider_ret;printf("case=%ld\n",provider_ret);
 assert(mcexec_path_readlinkat_bridge(-100,"path",buf,64)==expected);assert(mcexec_path_readlink_bridge("path",buf,64)==expected);
 assert(mcexec_path_fstatat_bridge(-100,"path",(void*)0x9999,0x100)==expected);assert(mcexec_path_stat_bridge("path",(void*)0x9999)==expected);assert(mcexec_path_faccessat_bridge(-100,"path",7,0x100)==expected);assert(mcexec_path_access_bridge("path",7)==expected);
 assert(mcexec_path_getxattr_bridge("path","name",(void*)0x9999,64)==expected);assert(mcexec_path_lgetxattr_bridge("path","name",(void*)0x9999,64)==expected);
 mcexec_path_openat_log_bridge(-100,"path",33);mcexec_path_open_log_bridge("path");assert(mcexec_path_openat_bridge(-100,"path",0x100000041UL,0x2000001edUL)==expected);assert(mcexec_path_open_bridge("path",0x100000041UL,0x2000001edUL)==expected);
 mcexec_cred_get_bridge(22,0x123456789abcdef0UL);assert(mcexec_cred_setfsuid_bridge(a)==provider_ret&&mcexec_cred_setfsgid_bridge(a)==provider_ret);assert(mcexec_cred_setuid_bridge(a)==expected&&mcexec_cred_setgid_bridge(a)==expected);assert(mcexec_cred_setreuid_bridge(a,b)==expected&&mcexec_cred_setregid_bridge(a,b)==expected);assert(mcexec_cred_setresuid_bridge(a,b,c)==expected&&mcexec_cred_setresgid_bridge(a,b,c)==expected);
 assert(mcexec_do_generic_syscall_raw_bridge(&w)==provider_ret);assert(mcexec_do_generic_syscall_bridge(&w)==expected);assert(mcexec_perf_event_open_bridge()==provider_ret);
 struct timespec tv;assert(mcexec_clock_gettime_bridge(7,&tv)==expected&&tv.tv_sec==123&&tv.tv_nsec==456);mcexec_clock_gettime_log_bridge(tv.tv_sec,tv.tv_nsec);
 }
 puts("platform-syscalls-fixture-complete");return 0;
}
