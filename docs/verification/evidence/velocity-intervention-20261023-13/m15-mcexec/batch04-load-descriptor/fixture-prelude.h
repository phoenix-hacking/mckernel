/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/mman.h>
#include <assert.h>
#include "reference-uprotocol.h"
extern int debug;
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
struct bitmask;
struct bitmask *numa_parse_nodestring_all(const char *);
int numa_max_possible_node(void);
int numa_bitmask_isbitset(const struct bitmask *,unsigned int);
void mcexec_numa_local_body(unsigned long *,unsigned long *,int);
void mcexec_numa_all_body(unsigned long *);
#define numa_local(cpu,mask) mcexec_numa_local_body(cpu,mask,0)
#define numa_nonlocal(cpu,mask) mcexec_numa_local_body(cpu,mask,1)
#define numa_all mcexec_numa_all_body
#define MCK_RLIMIT_AS	0
#define MCK_RLIMIT_CORE	1
#define MCK_RLIMIT_CPU	2
#define MCK_RLIMIT_DATA	3
#define MCK_RLIMIT_FSIZE	4
#define MCK_RLIMIT_LOCKS	5
#define MCK_RLIMIT_MEMLOCK	6
#define MCK_RLIMIT_MSGQUEUE	7
#define MCK_RLIMIT_NICE	8
#define MCK_RLIMIT_NOFILE	9
#define MCK_RLIMIT_NPROC	10
#define MCK_RLIMIT_RSS	11
#define MCK_RLIMIT_RTPRIO	12
#define MCK_RLIMIT_RTTIME	13
#define MCK_RLIMIT_SIGPENDING	14
#define MCK_RLIMIT_STACK	15

static int rlimits[] = {
#ifdef RLIMIT_AS
	RLIMIT_AS,	MCK_RLIMIT_AS,
#endif
#ifdef RLIMIT_CORE
	RLIMIT_CORE,	MCK_RLIMIT_CORE,
#endif
#ifdef RLIMIT_CPU
	RLIMIT_CPU,	MCK_RLIMIT_CPU,
#endif
#ifdef RLIMIT_DATA
	RLIMIT_DATA,	MCK_RLIMIT_DATA,
#endif
#ifdef RLIMIT_FSIZE
	RLIMIT_FSIZE,	MCK_RLIMIT_FSIZE,
#endif
#ifdef RLIMIT_LOCKS
	RLIMIT_LOCKS,	MCK_RLIMIT_LOCKS,
#endif
#ifdef RLIMIT_MEMLOCK
	RLIMIT_MEMLOCK,	MCK_RLIMIT_MEMLOCK,
#endif
#ifdef RLIMIT_MSGQUEUE
	RLIMIT_MSGQUEUE,MCK_RLIMIT_MSGQUEUE,
#endif
#ifdef RLIMIT_NICE
	RLIMIT_NICE,	MCK_RLIMIT_NICE,
#endif
#ifdef RLIMIT_NOFILE
	RLIMIT_NOFILE,	MCK_RLIMIT_NOFILE,
#endif
#ifdef RLIMIT_NPROC
	RLIMIT_NPROC,	MCK_RLIMIT_NPROC,
#endif
#ifdef RLIMIT_RSS
	RLIMIT_RSS,	MCK_RLIMIT_RSS,
#endif
#ifdef RLIMIT_RTPRIO
	RLIMIT_RTPRIO,	MCK_RLIMIT_RTPRIO,
#endif
#ifdef RLIMIT_RTTIME
	RLIMIT_RTTIME,	MCK_RLIMIT_RTTIME,
#endif
#ifdef RLIMIT_SIGPENDING
	RLIMIT_SIGPENDING,MCK_RLIMIT_SIGPENDING,
#endif
#ifdef RLIMIT_STACK
	RLIMIT_STACK,	MCK_RLIMIT_STACK,
#endif
};
struct program_load_desc *mcexec_load_alloc_desc_bridge(int nsections);
void mcexec_load_publish_main_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp);
void mcexec_desc_publish_interp_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp);
int *mcexec_load_cred_bridge(struct program_load_desc *desc);
long mcexec_load_clk_tck_bridge(void);
void mcexec_load_finalize_desc_bridge(struct program_load_desc *desc,
		int pid, int pgid, int reloc, unsigned long entry,
		unsigned long at_phdr, unsigned long at_phent,
		unsigned long at_phnum, unsigned long at_entry,
		unsigned long at_clktck, int stack_prot);
size_t mcexec_program_load_desc_size_bridge(void);
size_t mcexec_program_image_section_size_bridge(void);
void mcexec_desc_set_num_sections_bridge(struct program_load_desc *desc,
		int count);
void mcexec_desc_set_entry_bridge(struct program_load_desc *desc,
		unsigned long entry);
void mcexec_desc_set_interp_align_bridge(struct program_load_desc *desc,
		unsigned long align);
void mcexec_desc_set_args_len_bridge(struct program_load_desc *desc,
		unsigned long args_len);
int mcexec_desc_num_sections_bridge(const struct program_load_desc *desc);
int mcexec_desc_cpu_bridge(const struct program_load_desc *desc);
int mcexec_desc_pid_bridge(const struct program_load_desc *desc);
unsigned long mcexec_desc_entry_bridge(const struct program_load_desc *desc);
unsigned long mcexec_desc_rprocess_bridge(const struct program_load_desc *desc);
unsigned long mcexec_desc_section_vaddr_bridge(
		const struct program_load_desc *desc, int index);
unsigned long mcexec_desc_section_len_bridge(
		const struct program_load_desc *desc, int index);
unsigned long mcexec_desc_section_remote_pa_bridge(
		const struct program_load_desc *desc, int index);
unsigned long mcexec_desc_section_filesz_bridge(
		const struct program_load_desc *desc, int index);
unsigned long mcexec_desc_section_offset_bridge(
		const struct program_load_desc *desc, int index);
void *mcexec_desc_section_fp_bridge(
		const struct program_load_desc *desc, int index);
void mcexec_partition_publish_cpu_rank_bridge(struct program_load_desc *desc,
		int target_core, int process_rank);
void mcexec_partition_publish_rank_bridge(struct program_load_desc *desc,
		int process_rank);
void mcexec_desc_publish_mpol_base_bridge(struct program_load_desc *desc,
		int profile_arg, int nr_processes_arg, unsigned long flags,
		unsigned long threshold, unsigned long heap_ext,
		int pld_mpol_max);
void mcexec_desc_apply_bind_nodes_bridge(struct program_load_desc *desc,
		const char *nodes);
void mcexec_desc_apply_ompi_policy_bridge(struct program_load_desc *desc,
		int mode, int nodemask_action);
void mcexec_desc_publish_runtime_flags_bridge(struct program_load_desc *desc,
		int enable_uti_arg, int uti_thread_rank_arg,
		int uti_use_last_cpu_arg, int thp_disable_arg,
		int straight_map_arg, unsigned long straight_map_threshold_arg,
		int enable_tofu_arg, unsigned long mcexec_flags_arg);
void mcexec_desc_set_execve1_runtime_bridge(struct program_load_desc *desc,
		int vdso, unsigned long rlim_cur, unsigned long rlim_max,
		long prem);
void mcexec_main_stack_publish_bridge(struct program_load_desc *desc,
		rlim_t cur, rlim_t max, long prem);
void mcexec_desc_snapshot_rlimits_bridge(struct program_load_desc *desc);
void mcexec_desc_publish_env_bridge(struct program_load_desc *desc,
		int envs_len, char *envs);
void mcexec_desc_publish_args_cpu_bridge(struct program_load_desc *desc,
		unsigned long args_len, char *args, int cpu, int vdso);
void mcexec_desc_clear_flags_bridge(struct program_load_desc *desc);
