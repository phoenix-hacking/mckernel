#ifndef MCCTRL_RUST_H
#define MCCTRL_RUST_H

#include <linux/types.h>
#include <linux/string.h>
#include <linux/kernel.h>

#ifndef FUTEX_WAIT
#define FUTEX_WAIT 0
#endif
#ifndef FUTEX_WAKE
#define FUTEX_WAKE 1
#endif
#ifndef FUTEX_REQUEUE
#define FUTEX_REQUEUE 3
#endif
#ifndef FUTEX_CMP_REQUEUE
#define FUTEX_CMP_REQUEUE 4
#endif
#ifndef FUTEX_WAKE_OP
#define FUTEX_WAKE_OP 5
#endif
#ifndef FUTEX_WAIT_BITSET
#define FUTEX_WAIT_BITSET 9
#endif
#ifndef FUTEX_WAKE_BITSET
#define FUTEX_WAKE_BITSET 10
#endif
#ifndef FUTEX_WAIT_REQUEUE_PI
#define FUTEX_WAIT_REQUEUE_PI 11
#endif
#ifndef FUTEX_CMD_MASK
#define FUTEX_CMD_MASK 0x7f
#endif
#ifndef FUTEX_PRIVATE_FLAG
#define FUTEX_PRIVATE_FLAG 128
#endif
#ifndef FUTEX_CLOCK_REALTIME
#define FUTEX_CLOCK_REALTIME 256
#endif
#ifndef IHK_OS_AUX_PERF_NUM
#define IHK_OS_AUX_PERF_NUM        0x11290100
#endif
#ifndef IHK_OS_AUX_PERF_SET
#define IHK_OS_AUX_PERF_SET        0x11290101
#endif
#ifndef IHK_OS_AUX_PERF_GET
#define IHK_OS_AUX_PERF_GET        0x11290102
#endif
#ifndef IHK_OS_AUX_PERF_ENABLE
#define IHK_OS_AUX_PERF_ENABLE     0x11290103
#endif
#ifndef IHK_OS_AUX_PERF_DISABLE
#define IHK_OS_AUX_PERF_DISABLE    0x11290104
#endif
#ifndef IHK_OS_AUX_PERF_DESTROY
#define IHK_OS_AUX_PERF_DESTROY    0x11290105
#endif
#ifndef SCD_MSG_SYSCALL_ONESIDE
#define SCD_MSG_SYSCALL_ONESIDE    0x4
#endif
#ifndef MCCTRL_IKC_INIT_LAST_CHANNEL_PORT
#define MCCTRL_IKC_INIT_LAST_CHANNEL_PORT 502
#endif

#ifdef MCCTRL_RUST_HELPERS
unsigned long mcctrl_align_wait_buf_result(unsigned long size);
int mcctrl_partition_list_evict_result(int len, int max_len);
int mcctrl_partition_count_mismatch_result(int existing, int requested);
int mcctrl_partition_join_allowed_result(int joined, int total);
int mcctrl_partition_last_process_result(int left);
int mcctrl_partition_wait_required_result(int left, int woke_any, int woke_self);
unsigned int mcctrl_partition_wait_timeout_msecs_result(int nr_processes);
int mcctrl_partition_wake_next_result(int left);
unsigned long mcctrl_release_user_space_len_result(unsigned long start, unsigned long end);
int mcctrl_zero_mckernel_pages_step_result(unsigned long node_addr,
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
void mcctrl_zero_mckernel_pages_finish_result(unsigned long node_addr,
					     unsigned long zeroing_workers_offset);
int mcctrl_control_request_needs_root_result(unsigned int request);
int mcctrl_ikc_free_addrs_owner_result(int free_addrs_count);
int mcctrl_ikc_desc_free_at_put_result(int allocated_internally);
int mcctrl_ikc_wait_mode_result(long timeout);
unsigned long mcctrl_ikc_busy_timeout_msecs_result(long timeout);
int mcctrl_ikc_wait_abort_return_result(int wait_ret);
int mcctrl_ikc_release_packet_after_handler_result(int msg);
int mcctrl_ikc_cpu_nonnegative_result(int cpu);
int mcctrl_ikc_cpu_index_valid_result(int cpu, int num_channels);
int mcctrl_ikc_linux_cpu_valid_result(int linux_cpu, int nr_cpu_ids);
int mcctrl_ikc_init_uses_last_channel_result(int port);
int mcctrl_ikc_cpu_count_valid_result(int n_cpus);
int mcctrl_lwk_to_linux_index_result(const int *mapping, int count, int index);
int mcctrl_linux_to_lwk_index_result(const int *mapping, int count, int linux_id);
void mcctrl_fill_sequential_bitset_result(unsigned long *bits, int bit_count,
					  int word_count, int bits_per_word);
int mcctrl_read_buffer_status_result(char *buf, unsigned long size,
				     long bytes_read);
int mcctrl_parse_long_result(const char *buf, long *value_out);
int mcctrl_pci_realpath_valid_result(const char *path);
int mcctrl_ptr_hash_result(unsigned long ptr, unsigned long mask);
int mcctrl_ptr_eq_result(unsigned long a, unsigned long b);
int mcctrl_file_to_pidfd_lookup_match_result(unsigned long entry_filp,
					     unsigned long filp,
					     unsigned long entry_group_leader,
					     unsigned long group_leader);
int mcctrl_file_to_pidfd_remove_match_result(unsigned long entry_filp,
					    unsigned long filp,
					    unsigned long entry_os,
					    unsigned long os,
					    unsigned long entry_group_leader,
					    unsigned long group_leader,
					    int entry_fd, int fd);
int mcctrl_tofu_dev_path_result(const char *path);
unsigned long mcctrl_tofu_dev_tail_offset_result(void);
void mcctrl_tofu_dev_name_copy_result(char *dst, unsigned long dst_size,
				      const char *path);
int mcctrl_tofu_cq_path_parse_result(const char *path, int *tni_out,
				     int *cq_out);
int mcctrl_sysfs_path_error_result(const char *path, long written,
				   unsigned long path_size);
int mcctrl_binfmt_skip_path_result(const char *path);
int mcctrl_path_allowed_result(const char *file, const char *list);
int mcctrl_pager_treat_as_device_path_result(const char *path);
int mcctrl_pager_should_populate_path_result(const char *path);
int mcctrl_fs_is_tmpfs_result(const char *name);
int mcctrl_fs_is_proc_result(const char *name);
int mcctrl_special_char_device_result(unsigned int major, unsigned int minor);
int mcctrl_format_mcos_name_result(char *buf, unsigned long buflen, int osnum);
int mcctrl_format_decimal_name_result(char *buf, unsigned long buflen, int value);
int mcctrl_futex_cmd_result(int op);
int mcctrl_futex_is_private_result(int op);
int mcctrl_futex_clock_realtime_result(int op);
int mcctrl_futex_realtime_cmd_valid_result(int cmd);
int mcctrl_futex_wait_uses_timeout_result(int cmd);
int mcctrl_futex_arg3_is_val2_result(int cmd);
const char *mcctrl_futex_op_label_result(int cmd);

static inline unsigned long mcctrl_align_wait_buf(unsigned long size)
{
	return mcctrl_align_wait_buf_result(size);
}

static inline int mcctrl_partition_list_evict(int len, int max_len)
{
	return mcctrl_partition_list_evict_result(len, max_len);
}

static inline int mcctrl_partition_count_mismatch(int existing, int requested)
{
	return mcctrl_partition_count_mismatch_result(existing, requested);
}

static inline int mcctrl_partition_join_allowed(int joined, int total)
{
	return mcctrl_partition_join_allowed_result(joined, total);
}

static inline int mcctrl_partition_last_process(int left)
{
	return mcctrl_partition_last_process_result(left);
}

static inline int mcctrl_partition_wait_required(int left, int woke_any, int woke_self)
{
	return mcctrl_partition_wait_required_result(left, woke_any, woke_self);
}

static inline unsigned int mcctrl_partition_wait_timeout_msecs(int nr_processes)
{
	return mcctrl_partition_wait_timeout_msecs_result(nr_processes);
}

static inline int mcctrl_partition_wake_next(int left)
{
	return mcctrl_partition_wake_next_result(left);
}

static inline unsigned long mcctrl_release_user_space_len(unsigned long start,
							  unsigned long end)
{
	return mcctrl_release_user_space_len_result(start, end);
}

static inline int mcctrl_control_request_needs_root(unsigned int request)
{
	return mcctrl_control_request_needs_root_result(request);
}

static inline int mcctrl_ikc_free_addrs_owner(int free_addrs_count)
{
	return mcctrl_ikc_free_addrs_owner_result(free_addrs_count);
}

static inline int mcctrl_ikc_desc_free_at_put(int allocated_internally)
{
	return mcctrl_ikc_desc_free_at_put_result(allocated_internally);
}

static inline int mcctrl_ikc_wait_mode(long timeout)
{
	return mcctrl_ikc_wait_mode_result(timeout);
}

static inline unsigned long mcctrl_ikc_busy_timeout_msecs(long timeout)
{
	return mcctrl_ikc_busy_timeout_msecs_result(timeout);
}

static inline int mcctrl_ikc_wait_abort_return(int wait_ret)
{
	return mcctrl_ikc_wait_abort_return_result(wait_ret);
}

static inline int mcctrl_ikc_release_packet_after_handler(int msg)
{
	return mcctrl_ikc_release_packet_after_handler_result(msg);
}

static inline int mcctrl_ikc_cpu_nonnegative(int cpu)
{
	return mcctrl_ikc_cpu_nonnegative_result(cpu);
}

static inline int mcctrl_ikc_cpu_index_valid(int cpu, int num_channels)
{
	return mcctrl_ikc_cpu_index_valid_result(cpu, num_channels);
}

static inline int mcctrl_ikc_linux_cpu_valid(int linux_cpu, int nr_cpu_ids)
{
	return mcctrl_ikc_linux_cpu_valid_result(linux_cpu, nr_cpu_ids);
}

static inline int mcctrl_ikc_init_uses_last_channel(int port)
{
	return mcctrl_ikc_init_uses_last_channel_result(port);
}

static inline int mcctrl_ikc_cpu_count_valid(int n_cpus)
{
	return mcctrl_ikc_cpu_count_valid_result(n_cpus);
}

static inline int mcctrl_lwk_to_linux_index(const int *mapping, int count,
					    int index)
{
	return mcctrl_lwk_to_linux_index_result(mapping, count, index);
}

static inline int mcctrl_linux_to_lwk_index(const int *mapping, int count,
					    int linux_id)
{
	return mcctrl_linux_to_lwk_index_result(mapping, count, linux_id);
}

static inline void mcctrl_fill_sequential_bitset(unsigned long *bits,
						 int bit_count,
						 int word_count,
						 int bits_per_word)
{
	mcctrl_fill_sequential_bitset_result(bits, bit_count, word_count,
					     bits_per_word);
}

static inline int mcctrl_read_buffer_status(char *buf, unsigned long size,
					    long bytes_read)
{
	return mcctrl_read_buffer_status_result(buf, size, bytes_read);
}

static inline int mcctrl_parse_long(const char *buf, long *value_out)
{
	return mcctrl_parse_long_result(buf, value_out);
}

static inline int mcctrl_pci_realpath_valid(const char *path)
{
	return mcctrl_pci_realpath_valid_result(path);
}

static inline int mcctrl_ptr_hash(const void *ptr, unsigned long mask)
{
	return mcctrl_ptr_hash_result((unsigned long)ptr, mask);
}

static inline int mcctrl_ptr_eq(const void *a, const void *b)
{
	return mcctrl_ptr_eq_result((unsigned long)a, (unsigned long)b);
}

static inline int mcctrl_file_to_pidfd_lookup_match(
	const void *entry_filp, const void *filp,
	const void *entry_group_leader, const void *group_leader)
{
	return mcctrl_file_to_pidfd_lookup_match_result(
		(unsigned long)entry_filp, (unsigned long)filp,
		(unsigned long)entry_group_leader, (unsigned long)group_leader);
}

static inline int mcctrl_file_to_pidfd_remove_match(
	const void *entry_filp, const void *filp, const void *entry_os,
	const void *os, const void *entry_group_leader,
	const void *group_leader, int entry_fd, int fd)
{
	return mcctrl_file_to_pidfd_remove_match_result(
		(unsigned long)entry_filp, (unsigned long)filp,
		(unsigned long)entry_os, (unsigned long)os,
		(unsigned long)entry_group_leader, (unsigned long)group_leader,
		entry_fd, fd);
}

static inline int mcctrl_tofu_dev_path(const char *path)
{
	return mcctrl_tofu_dev_path_result(path);
}

static inline unsigned long mcctrl_tofu_dev_tail_offset(void)
{
	return mcctrl_tofu_dev_tail_offset_result();
}

static inline void mcctrl_tofu_dev_name_copy(char *dst, unsigned long dst_size,
					     const char *path)
{
	mcctrl_tofu_dev_name_copy_result(dst, dst_size, path);
}

static inline int mcctrl_tofu_cq_path_parse(const char *path, int *tni_out,
					    int *cq_out)
{
	return mcctrl_tofu_cq_path_parse_result(path, tni_out, cq_out);
}

static inline int mcctrl_sysfs_path_error(const char *path, long written,
					  unsigned long path_size)
{
	return mcctrl_sysfs_path_error_result(path, written, path_size);
}

static inline int mcctrl_binfmt_skip_path(const char *path)
{
	return mcctrl_binfmt_skip_path_result(path);
}

static inline int mcctrl_path_allowed(const char *file, const char *list)
{
	return mcctrl_path_allowed_result(file, list);
}

static inline int mcctrl_pager_treat_as_device_path(const char *path)
{
	return mcctrl_pager_treat_as_device_path_result(path);
}

static inline int mcctrl_pager_should_populate_path(const char *path)
{
	return mcctrl_pager_should_populate_path_result(path);
}

static inline int mcctrl_fs_is_tmpfs(const char *name)
{
	return mcctrl_fs_is_tmpfs_result(name);
}

static inline int mcctrl_fs_is_proc(const char *name)
{
	return mcctrl_fs_is_proc_result(name);
}

static inline int mcctrl_special_char_device(unsigned int major, unsigned int minor)
{
	return mcctrl_special_char_device_result(major, minor);
}

static inline int mcctrl_format_mcos_name(char *buf, unsigned long buflen, int osnum)
{
	return mcctrl_format_mcos_name_result(buf, buflen, osnum);
}

static inline int mcctrl_format_decimal_name(char *buf, unsigned long buflen, int value)
{
	return mcctrl_format_decimal_name_result(buf, buflen, value);
}

static inline int mcctrl_futex_cmd(int op)
{
	return mcctrl_futex_cmd_result(op);
}

static inline int mcctrl_futex_is_private(int op)
{
	return mcctrl_futex_is_private_result(op);
}

static inline int mcctrl_futex_clock_realtime(int op)
{
	return mcctrl_futex_clock_realtime_result(op);
}

static inline int mcctrl_futex_realtime_cmd_valid(int cmd)
{
	return mcctrl_futex_realtime_cmd_valid_result(cmd);
}

static inline int mcctrl_futex_wait_uses_timeout(int cmd)
{
	return mcctrl_futex_wait_uses_timeout_result(cmd);
}

static inline int mcctrl_futex_arg3_is_val2(int cmd)
{
	return mcctrl_futex_arg3_is_val2_result(cmd);
}

static inline const char *mcctrl_futex_op_label(int cmd)
{
	return mcctrl_futex_op_label_result(cmd);
}
#else
static inline unsigned long mcctrl_align_wait_buf(unsigned long size)
{
	return ((size + 63) >> 6) << 6;
}

static inline int mcctrl_partition_list_evict(int len, int max_len)
{
	return len >= max_len;
}

static inline int mcctrl_partition_count_mismatch(int existing, int requested)
{
	return existing != requested;
}

static inline int mcctrl_partition_join_allowed(int joined, int total)
{
	return joined < total;
}

static inline int mcctrl_partition_last_process(int left)
{
	return left == 0;
}

static inline int mcctrl_partition_wait_required(int left, int woke_any, int woke_self)
{
	return left || (woke_any && !woke_self);
}

static inline unsigned int mcctrl_partition_wait_timeout_msecs(int nr_processes)
{
	return 10000 + nr_processes * 100;
}

static inline int mcctrl_partition_wake_next(int left)
{
	return left != 0;
}

static inline unsigned long mcctrl_release_user_space_len(unsigned long start,
							  unsigned long end)
{
	return end - start;
}

static inline int mcctrl_control_request_needs_root(unsigned int request)
{
	return request == IHK_OS_AUX_PERF_NUM ||
		request == IHK_OS_AUX_PERF_SET ||
		request == IHK_OS_AUX_PERF_GET ||
		request == IHK_OS_AUX_PERF_ENABLE ||
		request == IHK_OS_AUX_PERF_DISABLE ||
		request == IHK_OS_AUX_PERF_DESTROY;
}

static inline int mcctrl_ikc_free_addrs_owner(int free_addrs_count)
{
	return free_addrs_count != 0;
}

static inline int mcctrl_ikc_desc_free_at_put(int allocated_internally)
{
	return allocated_internally != 0;
}

static inline int mcctrl_ikc_wait_mode(long timeout)
{
	return timeout < 0 ? -1 : timeout > 0 ? 1 : 0;
}

static inline unsigned long mcctrl_ikc_busy_timeout_msecs(long timeout)
{
	return -timeout;
}

static inline int mcctrl_ikc_wait_abort_return(int wait_ret)
{
	return wait_ret < 0 ? wait_ret : -ETIME;
}

static inline int mcctrl_ikc_release_packet_after_handler(int msg)
{
	return msg != SCD_MSG_SYSCALL_ONESIDE;
}

static inline int mcctrl_ikc_cpu_nonnegative(int cpu)
{
	return cpu >= 0;
}

static inline int mcctrl_ikc_cpu_index_valid(int cpu, int num_channels)
{
	return cpu >= 0 && cpu < num_channels;
}

static inline int mcctrl_ikc_linux_cpu_valid(int linux_cpu, int nr_cpu_ids)
{
	return linux_cpu <= nr_cpu_ids;
}

static inline int mcctrl_ikc_init_uses_last_channel(int port)
{
	return port == MCCTRL_IKC_INIT_LAST_CHANNEL_PORT;
}

static inline int mcctrl_ikc_cpu_count_valid(int n_cpus)
{
	return n_cpus >= 1;
}

static inline int mcctrl_lwk_to_linux_index(const int *mapping, int count,
					    int index)
{
	if (!mapping || index < 0 || index >= count)
		return -1;
	return mapping[index];
}

static inline int mcctrl_linux_to_lwk_index(const int *mapping, int count,
					    int linux_id)
{
	int i;

	if (!mapping || count <= 0)
		return -1;
	for (i = 0; i < count; ++i) {
		if (mapping[i] == linux_id)
			return i;
	}
	return -1;
}

static inline void mcctrl_fill_sequential_bitset(unsigned long *bits,
						 int bit_count,
						 int word_count,
						 int bits_per_word)
{
	int bit;

	if (!bits || bit_count < 0 || word_count <= 0 || bits_per_word <= 0)
		return;

	memset(bits, 0, sizeof(*bits) * word_count);
	for (bit = 0; bit < bit_count && bit < word_count * bits_per_word;
	     ++bit) {
		bits[bit / bits_per_word] |= 1UL << (bit % bits_per_word);
	}
}

static inline int mcctrl_read_buffer_status(char *buf, unsigned long size,
					    long bytes_read)
{
	if (bytes_read < 0)
		return bytes_read;
	if (!buf || bytes_read >= size)
		return -ENOSPC;
	buf[bytes_read] = '\0';
	return 0;
}

static inline int mcctrl_parse_long(const char *buf, long *value_out)
{
	return sscanf(buf, "%ld", value_out);
}

static inline int mcctrl_pci_realpath_valid(const char *path)
{
	return path && !strncmp(path, "../../../devices/", 17);
}

static inline int mcctrl_ptr_hash(const void *ptr, unsigned long mask)
{
	return (int)((unsigned long)ptr & mask);
}

static inline int mcctrl_ptr_eq(const void *a, const void *b)
{
	return a == b;
}

static inline int mcctrl_file_to_pidfd_lookup_match(
	const void *entry_filp, const void *filp,
	const void *entry_group_leader, const void *group_leader)
{
	return entry_filp == filp && entry_group_leader == group_leader;
}

static inline int mcctrl_file_to_pidfd_remove_match(
	const void *entry_filp, const void *filp, const void *entry_os,
	const void *os, const void *entry_group_leader,
	const void *group_leader, int entry_fd, int fd)
{
	return entry_filp == filp && entry_os == os &&
		entry_group_leader == group_leader && entry_fd == fd;
}

static inline int mcctrl_tofu_dev_path(const char *path)
{
	return path && !strncmp(path, "/proc/tofu/dev/", 15);
}

static inline unsigned long mcctrl_tofu_dev_tail_offset(void)
{
	return sizeof("/proc/tofu/dev/") - 1;
}

static inline void mcctrl_tofu_dev_name_copy(char *dst, unsigned long dst_size,
					     const char *path)
{
	if (!dst || !dst_size || !path)
		return;
	strncpy(dst, path + mcctrl_tofu_dev_tail_offset(), dst_size);
}

static inline int mcctrl_tofu_cq_path_parse(const char *path, int *tni_out,
					    int *cq_out)
{
	return path && sscanf(path, "/proc/tofu/dev/tni%dcq%d",
			      tni_out, cq_out) == 2;
}

static inline int mcctrl_sysfs_path_error(const char *path, long written,
					  unsigned long path_size)
{
	if ((unsigned long)written >= path_size)
		return -ENAMETOOLONG;
	if (!path || path[0] != '/')
		return -ENOENT;
	return 0;
}

static inline int mcctrl_binfmt_skip_path(const char *path)
{
	const char *cp;

	if (!path)
		return 1;

	cp = strrchr(path, '/');
	return !cp || !strcmp(cp, "/mcexec") ||
		!strcmp(cp, "/ihkosctl") || !strcmp(cp, "/ihkconfig");
}

static inline int mcctrl_path_allowed(const char *file, const char *list)
{
	const char *p;
	const char *q;
	const char *r;
	int l;

	if (!file || !list)
		return 0;
	if (!*list)
		return 1;
	p = list;
	do {
		q = strchr(p, ':');
		if (!q)
			q = strchr(p, '\0');
		for (r = q - 1; r >= p && *r == '/'; r--)
			;
		l = r - p + 1;

		if (!strncmp(file, p, l) && file[l] == '/')
			return 1;

		p = q + 1;
	} while (*q);
	return 0;
}

static inline int mcctrl_pager_treat_as_device_path(const char *path)
{
	return path && (!strncmp("/tmp/ompi.", path, 10) ||
		!strncmp("/dev/shm/", path, 9) ||
		(!strncmp("/var/opt/FJSVtcs/ple/daemonif/", path, 30) &&
		 !strstr(path, "dstore_sm.lock")));
}

static inline int mcctrl_pager_should_populate_path(const char *path)
{
	return path && (!strncmp("/tmp/ompi.", path, 10) ||
		!strncmp("/dev/shm/", path, 9) ||
		!strncmp("/var/opt/FJSVtcs/ple/daemonif/", path, 30));
}

static inline int mcctrl_fs_is_tmpfs(const char *name)
{
	return name && !strcmp(name, "tmpfs");
}

static inline int mcctrl_fs_is_proc(const char *name)
{
	return name && !strcmp(name, "proc");
}

static inline int mcctrl_special_char_device(unsigned int major, unsigned int minor)
{
	return major == 1 && (minor == 1 || minor == 5);
}

static inline int mcctrl_format_mcos_name(char *buf, unsigned long buflen, int osnum)
{
	return snprintf(buf, buflen, "mcos%d", osnum);
}

static inline int mcctrl_format_decimal_name(char *buf, unsigned long buflen, int value)
{
	return snprintf(buf, buflen, "%d", value);
}

static inline int mcctrl_futex_cmd(int op)
{
	return op & FUTEX_CMD_MASK;
}

static inline int mcctrl_futex_is_private(int op)
{
	return (op & FUTEX_PRIVATE_FLAG) != 0;
}

static inline int mcctrl_futex_clock_realtime(int op)
{
	return (op & FUTEX_CLOCK_REALTIME) != 0;
}

static inline int mcctrl_futex_realtime_cmd_valid(int cmd)
{
	return cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT_REQUEUE_PI;
}

static inline int mcctrl_futex_wait_uses_timeout(int cmd)
{
	return cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT;
}

static inline int mcctrl_futex_arg3_is_val2(int cmd)
{
	return cmd == FUTEX_CMP_REQUEUE || cmd == FUTEX_WAKE_OP;
}

static inline const char *mcctrl_futex_op_label(int cmd)
{
	return (cmd == FUTEX_WAIT) ? "FUTEX_WAIT" :
		(cmd == FUTEX_WAIT_BITSET) ? "FUTEX_WAIT_BITSET" :
		(cmd == FUTEX_WAKE) ? "FUTEX_WAKE" :
		(cmd == FUTEX_WAKE_OP) ? "FUTEX_WAKE_OP" :
		(cmd == FUTEX_WAKE_BITSET) ? "FUTEX_WAKE_BITSET" :
		(cmd == FUTEX_CMP_REQUEUE) ? "FUTEX_CMP_REQUEUE" :
		(cmd == FUTEX_REQUEUE) ? "FUTEX_REQUEUE (NOT IMPL!)" : "unknown";
}
#endif

#endif /* MCCTRL_RUST_H */
