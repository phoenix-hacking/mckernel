#pragma once
#include <stddef.h>
#define IHK_DEVICE_CREATE_OS          0x112900
#define IHK_DEVICE_DESTROY_OS         0x112901
#define IHK_DEVICE_RELEASE_CPU        0x112903
#define IHK_DEVICE_RELEASE_MEM        0x112905
#define IHK_DEVICE_QUERY_CPU          0x112906
#define IHK_DEVICE_QUERY_MEM          0x112907
#define IHK_DEVICE_GET_BUILDID        0x11290b
#define IHK_DEVICE_GET_NUM_CPUS       0x11290c
#define IHK_DEVICE_RESERVE_MEM_MAX_RATIO        0x11290e
#define IHK_DEVICE_DEBUG_START        0x122900
struct ihk_cpu_req {
	int *cpus;
	int num_cpus;
};
struct ihk_mem_req {
	size_t *sizes;
	int *numa_ids;
	int num_chunks;

	/* Limit of alloc_pages order when reserving.
	 * Use PAGE_SIZE for a system with system memory isolated,
	 * 32 KiB (1 MiB for "all") otherwise.
	 */
	int min_chunk_size;

	/* Stop gathering chunks for "all" request after accumulating
	 * this percentage
	 */
	int max_size_ratio_all;

	/* Give up proceeding to the smaller order when it took longer
	 * than this seconds for the current order
	 */
	int timeout;
};
