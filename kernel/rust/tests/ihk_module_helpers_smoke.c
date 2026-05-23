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
extern int ihk_core_load_file_mode_result(unsigned long load_file_addr,
		unsigned long load_mem_addr);
extern int ihk_core_file_size_valid_result(long long size);
extern int ihk_core_kernel_read_failed_result(long read_ret);
extern int ihk_core_load_file_continue_result(int ret,
		unsigned long long done, unsigned long long size);
extern unsigned int ihk_core_shutdown_status_policy_result(int status);
extern void ihk_core_kmsg_buf_init_result(unsigned long buf_addr,
		unsigned long lock_offset, unsigned long tail_offset,
		unsigned long len_offset, unsigned long head_offset,
		unsigned long str_offset, unsigned long str_len);
extern void ihk_core_kmsg_buf_clear_result(unsigned long buf_addr,
		unsigned long tail_offset, unsigned long head_offset,
		unsigned long str_offset, unsigned long str_len);
extern void ihk_core_kmsg_container_init_result(unsigned long cont_addr,
		unsigned long os_index_offset, unsigned long kmsg_buf_offset,
		unsigned long order_offset, int os_index,
		unsigned long kmsg_buf_addr, unsigned int order);
extern void ihk_core_atomic_set_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset, int value);
extern int ihk_core_atomic_read_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern void ihk_core_atomic_inc_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern void ihk_core_atomic_dec_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern int ihk_core_atomic_dec_return_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern int ihk_core_atomic_cmpxchg_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset, int old, int new);
extern unsigned long ihk_core_os_take_kmsg_container_result(
		unsigned long os_addr, unsigned long container_offset);
extern void ihk_core_list_add_tail_result(unsigned long entry_addr,
		unsigned long head_addr);
extern void ihk_core_list_del_result(unsigned long entry_addr,
		unsigned long poison_next, unsigned long poison_prev);
extern int ihk_core_list_contains_entry_result(unsigned long head_addr,
		unsigned long list_offset, unsigned long target_addr);
extern unsigned long ihk_core_list_next_entry_result(unsigned long head_addr,
		unsigned long list_offset, unsigned long cursor_addr);
extern unsigned long ihk_core_kmsg_find_by_os_index_reverse_result(
		unsigned long head_addr, unsigned long list_offset,
		unsigned long os_index_offset, int os_index);
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
extern int mcctrl_zero_mckernel_pages_step_result(unsigned long node_addr,
		unsigned long to_zero_list_offset,
		unsigned long zeroed_list_offset,
		unsigned long nr_to_zero_pages_offset,
		unsigned long free_chunk_addr_offset,
		unsigned long free_chunk_size_offset,
		unsigned long free_chunk_list_offset,
		unsigned long free_chunk_sizeof,
		unsigned long phys_to_virt_base,
		unsigned int page_shift,
		unsigned long *addr_out,
		unsigned long *size_out);
extern void mcctrl_zero_mckernel_pages_finish_result(unsigned long node_addr,
		unsigned long zeroing_workers_offset);
extern int ihk_smp_pack_available_cpus_result(const void *cpus, int cpu_count,
		unsigned long stride, unsigned long status_offset,
		int available_status, int *out, int capacity, int *needed);
extern int ihk_smp_pack_assigned_ikc_map_result(const void *cpus,
		int cpu_count, unsigned long stride, unsigned long status_offset,
		unsigned long os_offset, unsigned long ikc_offset,
		unsigned long target_os, int assigned_status, int *src_out,
		int *dst_out, int capacity, int *needed);
extern int ihk_smp_assign_scan_action_result(int chunk_numa,
		int requested_numa, unsigned long chunk_size,
		unsigned long requested_size, int has_max,
		unsigned long current_max_size, int has_match);
extern int ihk_smp_assign_no_chunk_action_result(unsigned long want,
		unsigned long all_marker, unsigned long size_left,
		unsigned long fake_chunk_size);
extern int ihk_smp_used_chunk_insert_before_result(unsigned long new_addr,
		unsigned long iter_addr);

#define BASE 0x100000UL
#define SHIFT 12U
#define OPEN_REF_INC 1
#define OPEN_REF_CMPXCHG 2
#define MINOR_FULL -1
#define MINOR_REUSE 0
#define MINOR_EXTEND 1
#define LOAD_FILE_NONE 0
#define LOAD_FILE_DIRECT 1
#define LOAD_FILE_MEM 2
#define OS_STATUS_NOT_BOOTED 0
#define OS_STATUS_LOADING 1
#define OS_STATUS_BOOTING 2
#define OS_STATUS_BOOTED 3
#define OS_STATUS_READY 4
#define OS_STATUS_RUNNING 5
#define OS_STATUS_FREEZING 6
#define OS_STATUS_FROZEN 7
#define OS_STATUS_SHUTDOWN 8
#define OS_STATUS_FAILED 9
#define OS_STATUS_HUNGUP 10
#define SHUTDOWN_WAIT_FROZEN 0x1U
#define SHUTDOWN_THAW 0x2U
#define SHUTDOWN_WAIT_READY 0x4U
#define SHUTDOWN_WAIT_RUNNING 0x8U
#define SHUTDOWN_NOT_BOOTED 0x10U
#define SHUTDOWN_BUSY 0x20U
#define SHUTDOWN_WARN_LOADING 0x40U
#define ASSIGN_SCAN_SKIP 0
#define ASSIGN_SCAN_UPDATE_MAX 1
#define ASSIGN_SCAN_EXACT 2
#define ASSIGN_NO_CHUNK_ERROR 0
#define ASSIGN_NO_CHUNK_ALL_DONE 1
#define ASSIGN_NO_CHUNK_FAKE_DONE 2
#define SMP_MEM_ALL (~0UL)
#define LIST_POISON_NEXT 0x11111111UL
#define LIST_POISON_PREV 0x22222222UL
#define STATUS_AVAILABLE 2
#define STATUS_ASSIGNED 3

struct fake_smp_cpu {
	int id;
	int hw_id;
	int status;
	unsigned long os;
	int ikc_map_cpu;
};

struct fake_kmsg_buf {
	int lock;
	int tail;
	int len;
	int head;
	char padding[16];
	char str[8];
};

struct fake_kmsg_container {
	char list[16];
	int os_index;
	int count;
	void *kmsg_buf;
	unsigned int order;
};

struct fake_os_data {
	char prefix[24];
	void *kmsg_buf_container;
};

struct fake_list_head {
	struct fake_list_head *next;
	struct fake_list_head *prev;
};

struct fake_llist_node {
	struct fake_llist_node *next;
};

struct fake_llist_head {
	struct fake_llist_node *first;
};

struct fake_zero_node {
	int id;
	int linux_numa_id;
	int type;
	int zeroing_workers;
	int nr_to_zero_pages;
	struct fake_llist_head zeroed_list;
	struct fake_llist_head to_zero_list;
};

struct fake_zero_chunk {
	unsigned long addr;
	unsigned long size;
	unsigned long rb_node[3];
	struct fake_llist_node list;
};

struct fake_kmsg_node {
	struct fake_list_head list;
	int os_index;
};

static void require(int condition)
{
	if (!condition)
		exit(2);
}

static int bytes_are_zero(const char *buf, int len)
{
	int i;

	for (i = 0; i < len; i++) {
		if (buf[i] != 0)
			return 0;
	}
	return 1;
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
	struct fake_kmsg_buf fake_kmsg = {
		.lock = 9,
		.tail = 7,
		.len = 6,
		.head = 5,
		.str = { 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h' },
	};
	struct fake_kmsg_container fake_cont = {
		.os_index = -1,
		.count = 99,
		.kmsg_buf = NULL,
		.order = 0,
	};
	struct fake_os_data fake_os = {
		.kmsg_buf_container = &fake_cont,
	};
	struct fake_list_head list_head;
	struct fake_list_head list_a;
	struct fake_list_head list_b;
	struct fake_list_head kmsg_head;
	struct fake_kmsg_node kmsg_a;
	struct fake_kmsg_node kmsg_b;
	unsigned char zero_backing[8192] __attribute__((aligned(64)));
	struct fake_zero_node zero_node = {
		.id = 3,
		.zeroing_workers = 1,
		.nr_to_zero_pages = 2,
	};
	struct fake_zero_chunk *zero_chunk_a =
		(struct fake_zero_chunk *)zero_backing;
	struct fake_zero_chunk *zero_chunk_b =
		(struct fake_zero_chunk *)(zero_backing + 4096);
	unsigned long zero_phys_base = 0x400000UL;
	unsigned long zero_virt_base =
		(unsigned long)zero_backing - zero_phys_base;
	unsigned long zero_addr = 0;
	unsigned long zero_size = 0;
	unsigned long old_container;
	int i;

	list_head.next = &list_head;
	list_head.prev = &list_head;
	list_a.next = &list_a;
	list_a.prev = &list_a;
	list_b.next = &list_b;
	list_b.prev = &list_b;
	kmsg_head.next = &kmsg_head;
	kmsg_head.prev = &kmsg_head;
	kmsg_a.list.next = &kmsg_a.list;
	kmsg_a.list.prev = &kmsg_a.list;
	kmsg_a.os_index = 4;
	kmsg_b.list.next = &kmsg_b.list;
	kmsg_b.list.prev = &kmsg_b.list;
	kmsg_b.os_index = 5;
	for (i = 0; i < (int)sizeof(zero_backing); i++)
		zero_backing[i] = 0x5a;
	zero_chunk_a->addr = zero_phys_base;
	zero_chunk_a->size = 4096;
	zero_chunk_a->list.next = &zero_chunk_b->list;
	zero_chunk_b->addr = zero_phys_base + 4096;
	zero_chunk_b->size = 4096;
	zero_chunk_b->list.next = NULL;
	zero_node.to_zero_list.first = &zero_chunk_a->list;
	zero_node.zeroed_list.first = NULL;

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
	require(ihk_core_load_file_mode_result(0x1000, 0x2000) ==
			LOAD_FILE_DIRECT);
	require(ihk_core_load_file_mode_result(0, 0x2000) == LOAD_FILE_MEM);
	require(ihk_core_load_file_mode_result(0, 0) == LOAD_FILE_NONE);
	require(ihk_core_file_size_valid_result(-1) == 0);
	require(ihk_core_file_size_valid_result(0) == 0);
	require(ihk_core_file_size_valid_result(1) == 1);
	require(ihk_core_kernel_read_failed_result(-5) == 1);
	require(ihk_core_kernel_read_failed_result(0) == 1);
	require(ihk_core_kernel_read_failed_result(7) == 0);
	require(ihk_core_load_file_continue_result(0, 0, 10) == 1);
	require(ihk_core_load_file_continue_result(0, 10, 10) == 0);
	require(ihk_core_load_file_continue_result(-1, 0, 10) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_SHUTDOWN) ==
			SHUTDOWN_BUSY);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FREEZING) ==
			(SHUTDOWN_WAIT_FROZEN | SHUTDOWN_THAW |
			 SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FROZEN) ==
			(SHUTDOWN_THAW | SHUTDOWN_WAIT_READY |
			 SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_BOOTING) ==
			(SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_BOOTED) ==
			(SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_READY) ==
			SHUTDOWN_WAIT_RUNNING);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_NOT_BOOTED) ==
			SHUTDOWN_NOT_BOOTED);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_LOADING) ==
			SHUTDOWN_WARN_LOADING);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_RUNNING) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FAILED) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_HUNGUP) == 0);
	require(ihk_core_shutdown_status_policy_result(999) == 0);
	ihk_core_kmsg_buf_init_result((unsigned long)&fake_kmsg,
			offsetof(struct fake_kmsg_buf, lock),
			offsetof(struct fake_kmsg_buf, tail),
			offsetof(struct fake_kmsg_buf, len),
			offsetof(struct fake_kmsg_buf, head),
			offsetof(struct fake_kmsg_buf, str),
			sizeof(fake_kmsg.str));
	require(fake_kmsg.lock == 0);
	require(fake_kmsg.tail == 0);
	require(fake_kmsg.len == (int)sizeof(fake_kmsg.str));
	require(fake_kmsg.head == 0);
	require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));
	fake_kmsg.lock = 1;
	fake_kmsg.tail = 4;
	fake_kmsg.head = 3;
	fake_kmsg.str[0] = 'z';
	fake_kmsg.str[7] = 'q';
	ihk_core_kmsg_buf_clear_result((unsigned long)&fake_kmsg,
			offsetof(struct fake_kmsg_buf, tail),
			offsetof(struct fake_kmsg_buf, head),
			offsetof(struct fake_kmsg_buf, str),
			sizeof(fake_kmsg.str));
	require(fake_kmsg.lock == 1);
	require(fake_kmsg.tail == 0);
	require(fake_kmsg.head == 0);
	require(fake_kmsg.len == (int)sizeof(fake_kmsg.str));
	require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));
	ihk_core_kmsg_container_init_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, os_index),
			offsetof(struct fake_kmsg_container, kmsg_buf),
			offsetof(struct fake_kmsg_container, order),
			12, (unsigned long)&fake_kmsg, 3);
	require(fake_cont.os_index == 12);
	require(fake_cont.count == 99);
	require(fake_cont.kmsg_buf == &fake_kmsg);
	require(fake_cont.order == 3);
	ihk_core_atomic_set_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 2);
	require(ihk_core_atomic_read_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count)) == 2);
	ihk_core_atomic_inc_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count));
	require(fake_cont.count == 3);
	ihk_core_atomic_dec_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count));
	require(fake_cont.count == 2);
	require(ihk_core_atomic_dec_return_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count)) == 1);
	require(fake_cont.count == 1);
	require(ihk_core_atomic_cmpxchg_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 1, 7) == 1);
	require(fake_cont.count == 7);
	require(ihk_core_atomic_cmpxchg_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 1, 9) == 7);
	require(fake_cont.count == 7);
	require(ihk_core_atomic_cmpxchg_i32_result(0,
			offsetof(struct fake_kmsg_container, count), 0, 1) == 0);
	old_container = ihk_core_os_take_kmsg_container_result(
			(unsigned long)&fake_os,
			offsetof(struct fake_os_data, kmsg_buf_container));
	require(old_container == (unsigned long)&fake_cont);
	require(fake_os.kmsg_buf_container == NULL);
	require(ihk_core_os_take_kmsg_container_result(0,
			offsetof(struct fake_os_data, kmsg_buf_container)) == 0);
	ihk_core_list_add_tail_result((unsigned long)&list_a,
			(unsigned long)&list_head);
	require(list_head.next == &list_a);
	require(list_head.prev == &list_a);
	require(list_a.next == &list_head);
	require(list_a.prev == &list_head);
	ihk_core_list_add_tail_result((unsigned long)&list_b,
			(unsigned long)&list_head);
	require(list_head.next == &list_a);
	require(list_head.prev == &list_b);
	require(list_a.next == &list_b);
	require(list_b.prev == &list_a);
	require(list_b.next == &list_head);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_a) == 1);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_b) == 1);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&kmsg_a) == 0);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next), 0) ==
			(unsigned long)&list_a);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_a) == (unsigned long)&list_b);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_b) == 0);
	ihk_core_list_del_result((unsigned long)&list_a,
			LIST_POISON_NEXT, LIST_POISON_PREV);
	require(list_head.next == &list_b);
	require(list_b.prev == &list_head);
	require(list_a.next == (struct fake_list_head *)LIST_POISON_NEXT);
	require(list_a.prev == (struct fake_list_head *)LIST_POISON_PREV);
	ihk_core_list_del_result((unsigned long)&list_b,
			LIST_POISON_NEXT, LIST_POISON_PREV);
	require(list_head.next == &list_head);
	require(list_head.prev == &list_head);
	ihk_core_list_add_tail_result((unsigned long)&kmsg_a.list,
			(unsigned long)&kmsg_head);
	ihk_core_list_add_tail_result((unsigned long)&kmsg_b.list,
			(unsigned long)&kmsg_head);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 5) ==
			(unsigned long)&kmsg_b);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 4) ==
			(unsigned long)&kmsg_a);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 9) == 0);

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
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_a),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 1);
	require(zero_addr == zero_phys_base);
	require(zero_size == 4096);
	require(zero_node.nr_to_zero_pages == 1);
	require(zero_node.to_zero_list.first == &zero_chunk_b->list);
	require(zero_node.zeroed_list.first == &zero_chunk_a->list);
	require(zero_chunk_a->list.next == NULL);
	require(bytes_are_zero((char *)zero_backing + sizeof(*zero_chunk_a),
			4096 - sizeof(*zero_chunk_a)));
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_b),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 1);
	require(zero_addr == zero_phys_base + 4096);
	require(zero_size == 4096);
	require(zero_node.nr_to_zero_pages == 0);
	require(zero_node.to_zero_list.first == NULL);
	require(zero_node.zeroed_list.first == &zero_chunk_b->list);
	require(zero_chunk_b->list.next == &zero_chunk_a->list);
	require(bytes_are_zero((char *)zero_backing + 4096 +
			sizeof(*zero_chunk_b), 4096 - sizeof(*zero_chunk_b)));
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_b),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 0);
	mcctrl_zero_mckernel_pages_finish_result((unsigned long)&zero_node,
			offsetof(struct fake_zero_node, zeroing_workers));
	require(zero_node.zeroing_workers == 0);

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
	require(ihk_smp_assign_scan_action_result(0, 1, 4096, 4096,
			0, 0, 0) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_scan_action_result(1, 1, 4096, 4096,
			0, 0, 0) == ASSIGN_SCAN_EXACT);
	require(ihk_smp_assign_scan_action_result(1, 1, 8192, 4096,
			0, 0, 0) == ASSIGN_SCAN_UPDATE_MAX);
	require(ihk_smp_assign_scan_action_result(1, 1, 4096, 8192,
			1, 16384, 0) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_scan_action_result(1, 1, 32768, 8192,
			1, 16384, 0) == ASSIGN_SCAN_UPDATE_MAX);
	require(ihk_smp_assign_scan_action_result(1, 1, 8192, 8192,
			1, 16384, 1) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_no_chunk_action_result(SMP_MEM_ALL,
			SMP_MEM_ALL, 4096, 0) == ASSIGN_NO_CHUNK_ALL_DONE);
	require(ihk_smp_assign_no_chunk_action_result(8192,
			SMP_MEM_ALL, 4096, 8192) == ASSIGN_NO_CHUNK_FAKE_DONE);
	require(ihk_smp_assign_no_chunk_action_result(8192,
			SMP_MEM_ALL, 16384, 8192) == ASSIGN_NO_CHUNK_ERROR);
	require(ihk_smp_used_chunk_insert_before_result(0x1000, 0x2000) == 1);
	require(ihk_smp_used_chunk_insert_before_result(0x3000, 0x2000) == 0);

	printf("ihk_module_helpers ok map=%016lx bits=%016lx/%016lx\n",
	       map[0], bits[0], bits[1]);
	return 0;
}
