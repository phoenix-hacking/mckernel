/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <setjmp.h>
#include <assert.h>
#include "reference-uprotocol.h"
#define ADD_ENVS_OPTION
#define PIN_SIZE 4096
extern int fd,debug;
struct thread_data_s;
static const char rlimit_stack_envname[]="MCKERNEL_RLIMIT_STACK";
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
#define __eprintf(format,args...) do {fprintf(stderr,"%s: " format,__func__,##args);fflush(stderr);} while(0)
ssize_t mcexec_find_libdir_body(char*,size_t);
#define find_libdir mcexec_find_libdir_body
long mcexec_util_thread_body(struct thread_data_s*,unsigned long,int,unsigned long,unsigned long,unsigned long);
#define util_thread mcexec_util_thread_body
void mcexec_kill_thread_body(unsigned long,unsigned long,void*);
void print_usage(char**);
int switch_ctx(int,unsigned long,struct uti_switch_ctx_desc*,void*,void*);
int mcexec_lookup_lstat_errno_bridge(const char *path);
int mcexec_load_desc_stat_size_bridge(const char *filename, long *size_out);
int mcexec_overlay_stat_exists_bridge(const char *path);
int mcexec_overlay_stat_errno_bridge(const char *path);
int mcexec_overlay_lstat_is_symlink_bridge(const char *path, int *is_symlink);
ssize_t mcexec_overlay_readlink_bridge(const char *path, char *out,
		size_t size);
int mcexec_overlay_find_libdir_bridge(char *out, size_t size);
void *mcexec_dma_mmap_bridge(void);
int mcexec_dma_mlock_bridge(void *buf);
int mcexec_create_ppd_bridge(void);
void mcexec_dma_mmap_failed_bridge(void);
void mcexec_dma_mlock_failed_bridge(void);
void mcexec_create_ppd_failed_bridge(void);
void mcexec_main_prepare_image_failed_bridge(void);
void mcexec_main_start_image_failed_bridge(void);
void mcexec_main_worker_threads_failed_bridge(int error);
void mcexec_flib_affinity_alloc_failed_bridge(void);
void mcexec_main_invalid_option_bridge(int opt, char **argv);
void mcexec_atobytes_set_errno_bridge(int value);
int mcexec_print_usage_add_envs_bridge(void);
void mcexec_print_usage_write_bridge(const char *line, size_t len);
void mcexec_kill_thread_bridge(unsigned long tid, unsigned long sig,
		struct thread_data_s *my_thread);
long mcexec_sched_setaffinity_util_bridge(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long uti_desc_arg);
int mcexec_util_thread_switch_ctx_bridge(struct uti_switch_ctx_desc *desc,
		void *lctx, void *rctx);
long mcexec_debug_mlock_bridge(unsigned long addr, unsigned long len);
void mcexec_debug_mlock_log_bridge(unsigned long addr, unsigned long len);
void mcexec_desc_mpol_log_bridge(const struct program_load_desc *desc);
void mcexec_reduce_stack_newval_overflow_bridge(void);
void mcexec_reduce_stack_setenv_failed_bridge(void);
void mcexec_main_stack_parse_failed_bridge(int parse_rc);
void mcexec_load_realloc_failed_bridge(unsigned long size);
void mcexec_load_desc_sections_bridge(int count);
void mcexec_print_desc_intro_bridge(const void *desc);
void mcexec_print_desc_main_bridge(int cpu, int pid, unsigned long entry,
		unsigned long rprocess);
void mcexec_print_desc_section_bridge(unsigned long vaddr,
		unsigned long len, unsigned long remote_pa,
		unsigned long filesz);
void mcexec_overlay_getdents_upper_bridge(int mck_ret, int ret,
		unsigned int count);
void mcexec_overlay_getdents_lower_bridge(int linux_ret, int ret,
		unsigned int count);
void mcexec_overlay_getdents_mck_size_log_bridge(size_t size, long offset,
		int len, unsigned int count);
void mcexec_overlay_getdents_linux_size_log_bridge(size_t size, long offset,
		int len, unsigned int count);
