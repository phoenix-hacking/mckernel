/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <sys/fsuid.h>
#include <sys/ioctl.h>
#include <time.h>
#include <assert.h>
extern int debug;
struct syscall_request {int rtid,ttid;unsigned long valid,number,args[6];};
struct syscall_wait_desc {unsigned long cpu;struct syscall_request sr;int pid;};
long mcexec_errno_return_result(long,int);
long mcexec_do_generic_syscall_body(const struct syscall_wait_desc *);
#define SET_ERR(ret) ((ret)=mcexec_errno_return_result((ret),errno))
#define MCEXEC_UP_GET_CRED 0x30a0290a
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
long mcexec_path_readlinkat_bridge(int dirfd, const char *path,
		char *buf, size_t size);
long mcexec_path_readlink_bridge(const char *path, char *buf, size_t size);
long mcexec_path_fstatat_bridge(int dirfd, const char *path,
		void *statbuf, int flags);
long mcexec_path_stat_bridge(const char *path, void *statbuf);
long mcexec_path_faccessat_bridge(int dirfd, const char *path,
		int mode, int flags);
long mcexec_path_access_bridge(const char *path, int mode);
long mcexec_path_getxattr_bridge(const char *path, const char *name,
		void *value, size_t size);
long mcexec_path_lgetxattr_bridge(const char *path, const char *name,
		void *value, size_t size);
void mcexec_path_openat_log_bridge(int dirfd, const char *path, int tid);
void mcexec_path_open_log_bridge(const char *path);
long mcexec_path_openat_bridge(int dirfd, const char *path,
		unsigned long flags, unsigned long mode);
long mcexec_path_open_bridge(const char *path, unsigned long flags,
		unsigned long mode);
void mcexec_cred_get_bridge(int mcos_fd, unsigned long arg);
long mcexec_cred_setfsuid_bridge(unsigned long uid);
long mcexec_cred_setfsgid_bridge(unsigned long gid);
long mcexec_cred_setresuid_bridge(unsigned long ruid,
		unsigned long euid, unsigned long suid);
long mcexec_cred_setresgid_bridge(unsigned long rgid,
		unsigned long egid, unsigned long sgid);
long mcexec_cred_setreuid_bridge(unsigned long ruid, unsigned long euid);
long mcexec_cred_setregid_bridge(unsigned long rgid, unsigned long egid);
long mcexec_cred_setuid_bridge(unsigned long uid);
long mcexec_cred_setgid_bridge(unsigned long gid);
long mcexec_do_generic_syscall_raw_bridge(struct syscall_wait_desc *w);
void mcexec_do_generic_syscall_start_bridge(unsigned long number);
void mcexec_do_generic_syscall_done_bridge(unsigned long number, long ret);
long mcexec_do_generic_syscall_bridge(struct syscall_wait_desc *w);
long mcexec_perf_event_open_bridge(void);
long mcexec_clock_gettime_bridge(int clock_id, struct timespec *tv);
void mcexec_clock_gettime_log_bridge(long sec, long nsec);
