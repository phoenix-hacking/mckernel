#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>

extern void ihk_core_pagealloc_reserve_padding_result(unsigned long *map,
		unsigned long mapsize, unsigned long mapaligned);
extern unsigned long ihk_core_pagealloc_large_alloc_result(unsigned long *map,
		unsigned long count, unsigned long last, int nblocks,
		unsigned long start, unsigned int shift);
extern unsigned long ihk_core_pagealloc_small_alloc_result(unsigned long *map,
		unsigned long count, unsigned long last, int npages,
		unsigned long start, unsigned int shift);
extern void ihk_core_pagealloc_free_blocks_result(unsigned long *map,
		unsigned long start, unsigned long address, int npages,
		unsigned int shift);
extern int ihk_core_open_ref_mode_result(int flags, int sharable_mask);
extern int ihk_core_open_exclusive_busy_result(int previous_refcount);
extern int ihk_core_open_callback_failed_result(int callback_ret);
extern int ihk_core_open_callback_present_result(unsigned long open_cb_addr);
extern int ihk_core_close_callback_present_result(unsigned long close_cb_addr);
extern int ihk_core_release_handler_present_result(unsigned long handler_addr);
extern int ihk_core_init_callback_present_result(unsigned long init_cb_addr);
extern int ihk_core_init_callback_failed_result(int init_ret);
extern int ihk_core_exit_callback_present_result(unsigned long exit_cb_addr);
extern int ihk_core_register_minor_action_result(int free_index,
		int current_max_minor, int max_minor);
extern int ihk_core_register_alloc_failed_result(unsigned long data_addr);
extern int ihk_core_register_should_shrink_minor_result(int minor,
		int current_max_minor);
extern int ihk_core_register_cdev_add_failed_result(int cdev_ret);
extern int ihk_core_register_device_create_failed_result(int is_error);
extern int ihk_core_refcount_busy_result(int refcount);
extern int ihk_core_kmsg_release_precheck_result(int refcount);
extern int ihk_core_kmsg_release_should_delete_result(int refcount_after_dec);
extern int ihk_core_kmsg_stray_delete_count_result(int nbufs, int max_bufs);
extern int ihk_core_destroy_callback_present_result(unsigned long destroy_cb_addr);
extern int ihk_core_destroy_callback_failed_result(int destroy_ret);
extern int ihk_core_destroy_os_pointer_invalid_result(unsigned long os_addr,
		unsigned long os_invalid_addr, unsigned long data_addr,
		unsigned long data_invalid_addr, unsigned long os_dev_data_addr);
extern int ihk_core_destroy_all_os_candidate_result(unsigned long os_addr,
		unsigned long os_invalid_addr, unsigned long os_dev_data_addr,
		unsigned long data_addr);
extern int ihk_core_destroy_all_os_should_restore_result(int destroy_ret);
extern int ihk_core_event_list_cleanup_needed_result(int list_empty);
extern int ihk_core_notifier_match_result(unsigned long entry_addr,
		unsigned long target_addr);
extern int ihk_core_notifier_should_add_result(int registered);
extern int ihk_core_notifier_should_remove_result(int registered);
extern int mcctrl_lwk_to_linux_index_result(const int *mapping, int count,
		int index);
extern int mcctrl_linux_to_lwk_index_result(const int *mapping, int count,
		int linux_id);
extern void mcctrl_fill_sequential_bitset_result(unsigned long *bits,
		int bit_count, int word_count, int bits_per_word);
extern int mcctrl_read_buffer_status_result(char *buf, unsigned long size,
		long bytes_read);
extern int mcctrl_parse_long_result(const char *buf, long *value_out);
extern int mcctrl_pci_realpath_valid_result(const char *path);
extern int mcctrl_ptr_hash_result(unsigned long ptr, unsigned long mask);
extern int mcctrl_ptr_eq_result(unsigned long a, unsigned long b);
extern int mcctrl_file_to_pidfd_lookup_match_result(unsigned long entry_filp,
		unsigned long filp, unsigned long entry_group_leader,
		unsigned long group_leader);
extern int mcctrl_file_to_pidfd_remove_match_result(unsigned long entry_filp,
		unsigned long filp, unsigned long entry_os, unsigned long os,
		unsigned long entry_group_leader, unsigned long group_leader,
		int entry_fd, int fd);
extern int mcctrl_tofu_dev_path_result(const char *path);
extern unsigned long mcctrl_tofu_dev_tail_offset_result(void);
extern void mcctrl_tofu_dev_name_copy_result(char *dst,
		unsigned long dst_size, const char *path);
extern int mcctrl_tofu_cq_path_parse_result(const char *path, int *tni_out,
		int *cq_out);
extern int mcctrl_sysfs_path_error_result(const char *path, long written,
		unsigned long path_size);
extern int ihk_smp_pack_available_cpus_result(const void *cpus, int cpu_count,
		unsigned long stride, unsigned long status_offset,
		int available_status, int *out, int capacity, int *needed);
extern int ihk_smp_pack_assigned_ikc_map_result(const void *cpus,
		int cpu_count, unsigned long stride, unsigned long status_offset,
		unsigned long os_offset, unsigned long ikc_offset,
		unsigned long target_os, int assigned_status, int *src_out,
		int *dst_out, int capacity, int *needed);

#define BASE 0x100000UL
#define SHIFT 12U
#define OPEN_REF_INC 1
#define OPEN_REF_CMPXCHG 2
#define MINOR_FULL -1
#define MINOR_REUSE 0
#define MINOR_EXTEND 1
#define STATUS_AVAILABLE 2
#define STATUS_ASSIGNED 3

struct fake_smp_cpu {
	int id;
	int hw_id;
	int status;
	unsigned long os;
	int ikc_map_cpu;
};

static void require(int condition)
{
	if (!condition)
		exit(2);
}

int main(void)
{
	unsigned long map[8] = { 0 };
	unsigned long padding[3] = { 0 };
	unsigned long bits[2] = { 0xaaaaaaaaaaaaaaaaUL, 0xbbbbbbbbbbbbbbbbUL };
	int mapping[] = { 4, 2, 7 };
	char read_buf[8] = { 'a', 'b', 'c', 'd', 'e', 'f', 'g', '\0' };
	long parsed = 0;
	unsigned long a;
	unsigned long b;
	struct fake_smp_cpu cpus[5] = {
		{ 0, 10, STATUS_AVAILABLE, 0, 0 },
		{ 1, 11, STATUS_ASSIGNED, 0x1000, 7 },
		{ 2, 12, STATUS_ASSIGNED, 0x2000, 8 },
		{ 3, 13, STATUS_AVAILABLE, 0, 0 },
		{ 4, 14, STATUS_ASSIGNED, 0x1000, 9 },
	};
	int out_cpus[3] = { -1, -1, -1 };
	int src_cpus[2] = { -1, -1 };
	int dst_cpus[2] = { -1, -1 };
	int needed = -1;
	int tni = -1;
	int cq = -1;
	char tofu_name[10] = { 'x', 'x', 'x', 'x', 'x',
		'x', 'x', 'x', 'x', 'x' };

	ihk_core_pagealloc_reserve_padding_result(padding, 130, 24);
	require(padding[0] == 0);
	require(padding[1] == 0);
	require(padding[2] == ~3UL);

	a = ihk_core_pagealloc_small_alloc_result(map, 8, 0, 3, BASE, SHIFT);
	require(a == BASE);
	require(map[0] == 0x7UL);

	b = ihk_core_pagealloc_small_alloc_result(map, 8, 0, 2, BASE, SHIFT);
	require(b == BASE + 3 * (1UL << SHIFT));
	require(map[0] == 0x1fUL);

	ihk_core_pagealloc_free_blocks_result(map, BASE, a, 3, SHIFT);
	require(map[0] == 0x18UL);

	a = ihk_core_pagealloc_large_alloc_result(map, 8, 0, 2, BASE, SHIFT);
	require(a == BASE + 64 * (1UL << SHIFT));
	require(map[1] == ~0UL);
	require(map[2] == ~0UL);
	require(ihk_core_pagealloc_large_alloc_result(map, 8, 0, 8,
			BASE, SHIFT) == 0);
	require(ihk_core_open_ref_mode_result(0x1, 0x1) == OPEN_REF_INC);
	require(ihk_core_open_ref_mode_result(0x0, 0x1) == OPEN_REF_CMPXCHG);
	require(ihk_core_open_exclusive_busy_result(0) == 0);
	require(ihk_core_open_exclusive_busy_result(2) == 1);
	require(ihk_core_open_callback_failed_result(0) == 0);
	require(ihk_core_open_callback_failed_result(-22) == 1);
	require(ihk_core_open_callback_present_result(0) == 0);
	require(ihk_core_open_callback_present_result(0x1000) == 1);
	require(ihk_core_close_callback_present_result(0) == 0);
	require(ihk_core_close_callback_present_result(0x1000) == 1);
	require(ihk_core_release_handler_present_result(0) == 0);
	require(ihk_core_release_handler_present_result(0x1000) == 1);
	require(ihk_core_init_callback_present_result(0) == 0);
	require(ihk_core_init_callback_present_result(0x1000) == 1);
	require(ihk_core_init_callback_failed_result(0) == 0);
	require(ihk_core_init_callback_failed_result(-1) == 1);
	require(ihk_core_exit_callback_present_result(0) == 0);
	require(ihk_core_exit_callback_present_result(0x1000) == 1);
	require(ihk_core_register_minor_action_result(1, 4, 8) == MINOR_REUSE);
	require(ihk_core_register_minor_action_result(4, 4, 8) == MINOR_EXTEND);
	require(ihk_core_register_minor_action_result(8, 8, 8) == MINOR_FULL);
	require(ihk_core_register_alloc_failed_result(0) == 1);
	require(ihk_core_register_alloc_failed_result(0x1000) == 0);
	require(ihk_core_register_should_shrink_minor_result(3, 4) == 1);
	require(ihk_core_register_should_shrink_minor_result(2, 4) == 0);
	require(ihk_core_register_cdev_add_failed_result(-1) == 1);
	require(ihk_core_register_cdev_add_failed_result(0) == 0);
	require(ihk_core_register_device_create_failed_result(1) == 1);
	require(ihk_core_register_device_create_failed_result(0) == 0);
	require(ihk_core_refcount_busy_result(0) == 0);
	require(ihk_core_refcount_busy_result(1) == 1);
	require(ihk_core_kmsg_release_precheck_result(0) == -22);
	require(ihk_core_kmsg_release_precheck_result(2) == 0);
	require(ihk_core_kmsg_release_should_delete_result(0) == 1);
	require(ihk_core_kmsg_release_should_delete_result(1) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(0, 4) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(3, 4) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(5, 4) == 2);
	require(ihk_core_destroy_callback_present_result(0) == 0);
	require(ihk_core_destroy_callback_present_result(0x1000) == 1);
	require(ihk_core_destroy_callback_failed_result(0) == 0);
	require(ihk_core_destroy_callback_failed_result(-5) == 1);
	require(ihk_core_destroy_os_pointer_invalid_result(0x1000, ~0UL,
			0x2000, ~0UL, 0x2000) == 0);
	require(ihk_core_destroy_os_pointer_invalid_result(0, ~0UL,
			0x2000, ~0UL, 0x2000) == 1);
	require(ihk_core_destroy_os_pointer_invalid_result(0x1000, ~0UL,
			0x2000, ~0UL, 0x3000) == 1);
	require(ihk_core_destroy_all_os_candidate_result(0x1000, ~0UL,
			0x2000, 0x2000) == 1);
	require(ihk_core_destroy_all_os_candidate_result(0, ~0UL,
			0x2000, 0x2000) == 0);
	require(ihk_core_destroy_all_os_candidate_result(0x1000, ~0UL,
			0x3000, 0x2000) == 0);
	require(ihk_core_destroy_all_os_should_restore_result(0) == 0);
	require(ihk_core_destroy_all_os_should_restore_result(-16) == 1);
	require(ihk_core_event_list_cleanup_needed_result(0) == 1);
	require(ihk_core_event_list_cleanup_needed_result(1) == 0);
	require(ihk_core_notifier_match_result(0x1000, 0x1000) == 1);
	require(ihk_core_notifier_match_result(0x1000, 0x2000) == 0);
	require(ihk_core_notifier_should_add_result(0) == 1);
	require(ihk_core_notifier_should_add_result(1) == 0);
	require(ihk_core_notifier_should_remove_result(0) == 0);
	require(ihk_core_notifier_should_remove_result(1) == 1);

	require(mcctrl_lwk_to_linux_index_result(mapping, 3, 1) == 2);
	require(mcctrl_lwk_to_linux_index_result(mapping, 3, -1) == -1);
	require(mcctrl_lwk_to_linux_index_result(mapping, 3, 3) == -1);
	require(mcctrl_linux_to_lwk_index_result(mapping, 3, 7) == 2);
	require(mcctrl_linux_to_lwk_index_result(mapping, 3, 5) == -1);

	mcctrl_fill_sequential_bitset_result(bits, 70, 2, 64);
	require(bits[0] == ~0UL);
	require(bits[1] == 0x3fUL);

	mcctrl_fill_sequential_bitset_result(bits, 3, 2, 64);
	require(bits[0] == 0x7UL);
	require(bits[1] == 0);

	require(mcctrl_read_buffer_status_result(read_buf, sizeof(read_buf), 3) == 0);
	require(read_buf[3] == '\0');
	require(mcctrl_read_buffer_status_result(read_buf, 3, 3) == -28);
	require(mcctrl_read_buffer_status_result(read_buf, sizeof(read_buf), -5) == -5);
	require(mcctrl_parse_long_result(" \t-42tail", &parsed) == 1);
	require(parsed == -42);
	require(mcctrl_parse_long_result("not-a-number", &parsed) == 0);
	require(mcctrl_pci_realpath_valid_result("../../../devices/pci0000:00") == 1);
	require(mcctrl_pci_realpath_valid_result("../../wrong") == 0);
	require(mcctrl_ptr_hash_result(0x1234, 0xff) == 0x34);
	require(mcctrl_ptr_eq_result(0x1234, 0x1234) == 1);
	require(mcctrl_ptr_eq_result(0x1234, 0x1235) == 0);
	require(mcctrl_file_to_pidfd_lookup_match_result(1, 1, 2, 2) == 1);
	require(mcctrl_file_to_pidfd_lookup_match_result(1, 1, 2, 3) == 0);
	require(mcctrl_file_to_pidfd_remove_match_result(1, 1, 2, 2, 3, 3,
			4, 4) == 1);
	require(mcctrl_file_to_pidfd_remove_match_result(1, 1, 2, 2, 3, 3,
			4, 5) == 0);
	require(mcctrl_tofu_dev_path_result("/proc/tofu/dev/tni1cq2") == 1);
	require(mcctrl_tofu_dev_path_result("/proc/other") == 0);
	require(mcctrl_tofu_dev_tail_offset_result() == 15);
	mcctrl_tofu_dev_name_copy_result(tofu_name, sizeof(tofu_name),
			"/proc/tofu/dev/a");
	require(tofu_name[0] == 'a');
	require(tofu_name[1] == '\0');
	require(tofu_name[9] == '\0');
	require(mcctrl_tofu_cq_path_parse_result("/proc/tofu/dev/tni12cq34",
			&tni, &cq) == 1);
	require(tni == 12 && cq == 34);
	require(mcctrl_tofu_cq_path_parse_result("/proc/tofu/dev/tni12xx34",
			&tni, &cq) == 0);
	require(mcctrl_sysfs_path_error_result("/sys/test", 9, 32) == 0);
	require(mcctrl_sysfs_path_error_result("sys/test", 8, 32) == -2);
	require(mcctrl_sysfs_path_error_result("/sys/test", 32, 32) == -36);

	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, NULL, 0, &needed) == 0);
	require(needed == 2);
	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, out_cpus, 3, &needed) == 0);
	require(needed == 2 && out_cpus[0] == 0 && out_cpus[1] == 3);
	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, out_cpus, 1, &needed) == -22);
	require(needed == 2);
	require(ihk_smp_pack_assigned_ikc_map_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			offsetof(struct fake_smp_cpu, os),
			offsetof(struct fake_smp_cpu, ikc_map_cpu), 0x1000,
			STATUS_ASSIGNED, src_cpus, dst_cpus, 2, &needed) == 0);
	require(needed == 2 && src_cpus[0] == 1 && dst_cpus[0] == 7 &&
			src_cpus[1] == 4 && dst_cpus[1] == 9);
	require(ihk_smp_pack_assigned_ikc_map_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			offsetof(struct fake_smp_cpu, os),
			offsetof(struct fake_smp_cpu, ikc_map_cpu), 0x1000,
			STATUS_ASSIGNED, src_cpus, dst_cpus, 1, &needed) == -22);
	require(needed == 2);

	printf("ihk_module_helpers ok map=%016lx bits=%016lx/%016lx\n",
	       map[0], bits[0], bits[1]);
	return 0;
}
