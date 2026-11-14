/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/cacheinfo.h>
#include <linux/cpumask.h>
#include <linux/stddef.h>
#include <asm/processor.h>

const unsigned long mckernel_native_topology_layout[]
__attribute__((section(".mckernel_native_topology_layout"), used)) = {
	sizeof(struct cpuinfo_x86), __alignof__(struct cpuinfo_x86),
	offsetof(struct cpuinfo_x86, topo),
	sizeof(struct cpuinfo_topology), __alignof__(struct cpuinfo_topology),
	offsetof(struct cpuinfo_topology, pkg_id),
	offsetof(struct cpuinfo_topology, core_id),
	offsetof(struct cpuinfo_topology, apicid),
	offsetof(struct cpuinfo_topology, initial_apicid),
	offsetof(struct cpuinfo_topology, die_id),
	sizeof(cpumask_t), __alignof__(cpumask_t),
	offsetof(struct cpumask, bits), sizeof(unsigned long),
	sizeof(struct cacheinfo), __alignof__(struct cacheinfo),
	offsetof(struct cacheinfo, id), offsetof(struct cacheinfo, type),
	offsetof(struct cacheinfo, level),
	offsetof(struct cacheinfo, coherency_line_size),
	offsetof(struct cacheinfo, number_of_sets),
	offsetof(struct cacheinfo, ways_of_associativity),
	offsetof(struct cacheinfo, physical_line_partition),
	offsetof(struct cacheinfo, size),
	offsetof(struct cacheinfo, shared_cpu_map),
	offsetof(struct cacheinfo, attributes),
	offsetof(struct cacheinfo, disable_sysfs),
	sizeof(struct cpu_cacheinfo), __alignof__(struct cpu_cacheinfo),
	offsetof(struct cpu_cacheinfo, info_list),
	offsetof(struct cpu_cacheinfo, per_cpu_data_slice_size),
	offsetof(struct cpu_cacheinfo, num_levels),
	offsetof(struct cpu_cacheinfo, num_leaves),
	offsetof(struct cpu_cacheinfo, cpu_map_populated),
	offsetof(struct cpu_cacheinfo, early_ci_levels),
	CACHE_TYPE_NOCACHE, CACHE_TYPE_INST, CACHE_TYPE_DATA,
	CACHE_TYPE_SEPARATE, CACHE_TYPE_UNIFIED, CACHE_ID,
	sizeof(unsigned int), sizeof(void *), CONFIG_NR_CPUS,
	offsetof(struct cpuinfo_x86, cpu_index),
};
