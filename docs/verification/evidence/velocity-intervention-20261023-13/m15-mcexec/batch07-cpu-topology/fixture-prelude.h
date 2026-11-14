/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sched.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <sys/ioctl.h>
#include <assert.h>
#include "reference-uprotocol.h"
extern int fd,ncpu,nnodes,debug;
extern void *numa_nodes;
extern size_t cpu_set_size;
extern cpu_set_t mcexec_partition_cpu_set_storage;
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
static cpu_set_t *numa_node_set(int n) {return (cpu_set_t *)((char*)numa_nodes+n*cpu_set_size);}
int numa_run_on_node(int);
int mcexec_numa_node_cpu_isset_bridge(int node, int cpu);
int mcexec_main_get_cpu_bridge(void);
int mcexec_main_get_nodes_bridge(void);
void mcexec_main_no_cpu_bridge(void);
void mcexec_main_no_numa_node_bridge(void);
void mcexec_main_alloc_nodes_error_bridge(void);
size_t mcexec_main_cpu_alloc_size_bridge(int cpu_count);
void mcexec_main_publish_topology_bridge(int cpu_count, int node_count,
		size_t node_set_size, void *nodes);
void mcexec_main_numa_node_zero_bridge(void *nodes, size_t node_set_size,
		int node_id);
int mcexec_main_node_cpu_exists_bridge(int node_id, int cpu);
void mcexec_main_numa_node_set_cpu_bridge(void *nodes, size_t node_set_size,
		int node_id, int cpu);
int mcexec_overlay_cpu_in_node_bridge(int cpu, int node);
int mcexec_partition_get_cpuset_bridge(struct program_load_desc *desc,
		int nr_processes, int *target_core, int *process_rank,
		int *mcexec_linux_numa, int *ikc_mapped);
void mcexec_partition_get_cpuset_failed_bridge(void);
int mcexec_partition_sched_setaffinity_bridge(void);
int mcexec_partition_numa_run_bridge(int mcexec_linux_numa);
void mcexec_numa_local_cpu_log_bridge(int cpu);
void mcexec_numa_node_cpu_log_bridge(int cpu, int node);
void mcexec_process_thread_plan_flib_log_bridge(int planned_nr_processes);
void mcexec_partition_rank_log_bridge(int process_rank, int target_core);
void mcexec_partition_sched_setaffinity_warning_bridge(void);
void mcexec_partition_numa_run_warning_bridge(int mcexec_linux_numa);
