#pragma once
#include <stddef.h>
#define IHK_MAX_NUM_CPUS 1024
#define IHK_KMSG_SIZE ((4 << 20)-4096)
#define DUMP_LEVEL_ALL 0
#define IHK_OS_LOAD                   0x112a00
#define IHK_OS_BOOT                   0x112a01
#define IHK_OS_SHUTDOWN               0x112a02
#define IHK_OS_QUERY_STATUS           0x112a03
#define IHK_OS_SET_KARGS              0x112a04
#define IHK_OS_QUERY_FREE_MEM         0x112a05
#define IHK_OS_DUMP                   0x112a06
#define IHK_OS_ALLOC_CPU              0x112a10
#define IHK_OS_ALLOC_MEM              0x112a11
#define IHK_OS_RESERVE_CPU            0x112a12
#define IHK_OS_RESERVE_MEM            0x112a13
#define IHK_OS_STATUS                 0x112a14
#define IHK_OS_REGISTER_EVENT         0x112a15
#define IHK_OS_EVENTFD                0x112a16
#define IHK_OS_READ_KMSG              0x112a20
#define IHK_OS_CLEAR_KMSG             0x112a21
#define IHK_OS_ASSIGN_CPU             0x112a22
#define IHK_OS_RELEASE_CPU            0x112a23
#define IHK_OS_ASSIGN_MEM             0x112a24
#define IHK_OS_RELEASE_MEM            0x112a25
#define IHK_OS_QUERY_CPU              0x112a26
#define IHK_OS_QUERY_MEM              0x112a27
#define IHK_OS_SET_IKC_MAP            0x112a28
#define IHK_OS_GET_IKC_MAP            0x112a29
#define IHK_OS_FREEZE                 0x112a30
#define IHK_OS_THAW                   0x112a31
#define IHK_OS_GET_USAGE              0x112a32
#define IHK_OS_GET_CPU_USAGE          0x112a33
#define IHK_OS_GET_NUM_NUMA_NODES     0x112a34
#define IHK_OS_NOTIFY_HUNGUP          0x112a35
#define IHK_OS_GET_BUILDID            0x112a37
#define IHK_OS_GET_NUM_CPUS           0x112a38
#define IHK_OS_READ_KADDR             0x112a39
#define IHK_OS_DEBUG_START            0x122a00
#define IHK_OS_DEBUG_END              0x122aff
#define IHK_OS_READ_KADDR_VIRT	0
#define IHK_OS_READ_KADDR_PHYS	1
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
struct ihk_ikc_req {
	int *src_cpus;	/* LWC CPUs as IKC source */
	int *dst_cpus;	/* Linux CPUs as IKC destination */
	int num_cpus;
};
