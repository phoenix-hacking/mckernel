#pragma once
#include <ihk/ihk_host_user.h>
struct ihk_mem_chunk {
	unsigned long size;
	int numa_node_number;
};
int ihk_reserve_cpu(int index, int* cpus, int num_cpus);
int ihk_reserve_mem(int index, struct ihk_mem_chunk* mem_chunks, int num_mem_chunks);
int ihk_get_num_os_instances(int index);
int ihk_get_os_instances(int index, int *indices, int _num_os_instances);
