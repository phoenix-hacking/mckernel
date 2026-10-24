/* Functional OS/apps and Rust migration only; no security testing. Exact selected ABI. */
#ifndef SELECTED_MEMORY_LAYOUT_H
#define SELECTED_MEMORY_LAYOUT_H
#include <stddef.h>
#include <stdint.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihklib.h>
struct ihklib_reserve_mem_conf {
	/* 1: Try to reserve the sum of the requested per-NUMA-node
	 *    amounts in a balanced way. It reports an error when the
	 *    variance of the reserved amounts of the NUMA-nodes
	 *    exceeds the "variance_limit" below.
	 */
	int balanced_enable;

	/* 1: Perform best-effort reservation of the size up to the
	 *    requested size, i.e. it's allowed to lower the reservation
	 *    size to the available if the latter is less than the former.
	 */
	int balanced_best_effort;

	/* MAX(max - ave, ave - min) must be less than or equal to
	 * ave * variance_limit / 100
	 */
	int balanced_variance_limit;

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
extern struct ihklib_reserve_mem_conf ref_reserve_mem_conf;
#endif
