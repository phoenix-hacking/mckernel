/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <ihk/debug.h>
#include <mc_perf_event.h>
#include <ihk/memconst.h>
#ifndef ENABLE_PERF
#error "This fixture is the actual selected ENABLE_PERF profile"
#endif
typedef long (*syscall_copy_from_user_fn_t)(void *dst,
		unsigned long src_addr, size_t bytes);
typedef int (*perf_attr_freq_fn_t)(const void *attr);
typedef int (*perf_open_event_alloc_fn_t)(void **event_out, void *attr);
typedef int (*perf_counter_alloc_fn_t)(void *thread, void *event);
typedef long (*perf_open_syscall_fn_t)(struct syscall_request *request,
		int cpu);
typedef void *(*syscall_policy_alloc_fn_t)(size_t size, unsigned long flags);
typedef long (*syscall_mckfd_long_fn_t)(struct mckfd *fdp,
		ihk_mc_user_context_t *ctx);
typedef int (*syscall_mckfd_int_fn_t)(struct mckfd *fdp,
		ihk_mc_user_context_t *ctx);
typedef long (*syscall_mckfd_lock_fn_t)(void *lock);
typedef void (*syscall_mckfd_unlock_fn_t)(void *lock, long irqstate);
extern long perf_event_open_entry_body_result(
		struct syscall_request *request, void *thread, void *proc,
		void *attr, unsigned long user_attr_addr, size_t attr_size,
		size_t attr_type_offset, size_t attr_read_format_offset,
		size_t attr_sample_period_offset, int pid, int validation_cpu,
		int group_fd, unsigned long flags, int linux_cpu,
		unsigned long raw_type, unsigned long hardware_type,
		unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit, int perf_event_open_nr,
		size_t mckfd_size, unsigned long mckfd_alloc_flags,
		size_t event_pid_offset, size_t event_counter_id_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		perf_attr_freq_fn_t attr_freq_fn,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
long fixture_copy(void *,unsigned long,size_t);
int fixture_frequency(const void *);
int fixture_event(void **,void *);
int fixture_counter(void *,void *);
long fixture_syscall(struct syscall_request *,int);
void *fixture_descriptor(size_t,unsigned long);
long fixture_read(struct mckfd *,ihk_mc_user_context_t *);
int fixture_ioctl(struct mckfd *,ihk_mc_user_context_t *);
long fixture_mmap(struct mckfd *,ihk_mc_user_context_t *);
int fixture_close(struct mckfd *,ihk_mc_user_context_t *);
int fixture_fcntl(struct mckfd *,ihk_mc_user_context_t *);
long fixture_lock(void *);
void fixture_unlock(void *,long);
#define syscall_copy_from_user_bridge fixture_copy
#define perf_event_open_attr_freq_bridge fixture_frequency
#define perf_event_open_alloc_event_bridge fixture_event
#define perf_event_open_counter_alloc_bridge fixture_counter
#define perf_event_open_do_syscall_bridge fixture_syscall
#define perf_event_alloc_kmalloc_bridge fixture_descriptor
#define perf_read fixture_read
#define perf_ioctl fixture_ioctl
#define perf_mmap fixture_mmap
#define perf_close fixture_close
#define perf_fcntl fixture_fcntl
#define syscall_mckfd_lock_bridge fixture_lock
#define syscall_mckfd_unlock_bridge fixture_unlock
struct f03_perf_entry_layout_v1 {
 unsigned long raw_type;
 unsigned long hardware_type;
 unsigned long hw_cache_type;
 unsigned long unsupported_read_format_mask;
 unsigned long sample_period_sign_bit;
 int perf_event_open_nr;
 size_t mckfd_size;
 unsigned long mckfd_alloc_flags;
 size_t event_pid_offset;
 size_t event_counter_id_offset;
 size_t proc_mckfd_offset;
 size_t mckfd_next_offset;
 size_t mckfd_fd_offset;
 size_t mckfd_data_offset;
 size_t event_group_leader_offset;
 size_t event_sibling_list_offset;
 size_t event_group_entry_offset;
 size_t event_nr_siblings_offset;
 size_t event_pmc_status_offset;
 size_t thread_pmc_alloc_map_offset;
 size_t proc_mckfd_lock_offset;
 size_t mckfd_sig_no_offset;
 size_t mckfd_read_cb_offset;
 size_t mckfd_ioctl_cb_offset;
 size_t mckfd_mmap_cb_offset;
 size_t mckfd_close_cb_offset;
 size_t mckfd_fcntl_cb_offset;
};
const struct f03_perf_entry_layout_v1 f03_perf_entry_layout_v1 = {
 .raw_type = PERF_TYPE_RAW,
 .hardware_type = PERF_TYPE_HARDWARE,
 .hw_cache_type = PERF_TYPE_HW_CACHE,
 .unsupported_read_format_mask = PERF_FORMAT_TOTAL_TIME_ENABLED |
			PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID,
 .sample_period_sign_bit = 1UL << 63,
 .perf_event_open_nr = __NR_perf_event_open,
 .mckfd_size = sizeof(struct mckfd),
 .mckfd_alloc_flags = IHK_MC_AP_NOWAIT,
 .event_pid_offset = __builtin_offsetof(struct mc_perf_event, pid),
 .event_counter_id_offset = __builtin_offsetof(struct mc_perf_event, counter_id),
 .proc_mckfd_offset = __builtin_offsetof(struct process, mckfd),
 .mckfd_next_offset = __builtin_offsetof(struct mckfd, next),
 .mckfd_fd_offset = __builtin_offsetof(struct mckfd, fd),
 .mckfd_data_offset = __builtin_offsetof(struct mckfd, data),
 .event_group_leader_offset = __builtin_offsetof(struct mc_perf_event, group_leader),
 .event_sibling_list_offset = __builtin_offsetof(struct mc_perf_event, sibling_list),
 .event_group_entry_offset = __builtin_offsetof(struct mc_perf_event, group_entry),
 .event_nr_siblings_offset = __builtin_offsetof(struct mc_perf_event, nr_siblings),
 .event_pmc_status_offset = __builtin_offsetof(struct mc_perf_event, pmc_status),
 .thread_pmc_alloc_map_offset = __builtin_offsetof(struct thread, pmc_alloc_map),
 .proc_mckfd_lock_offset = __builtin_offsetof(struct process, mckfd_lock),
 .mckfd_sig_no_offset = __builtin_offsetof(struct mckfd, sig_no),
 .mckfd_read_cb_offset = __builtin_offsetof(struct mckfd, read_cb),
 .mckfd_ioctl_cb_offset = __builtin_offsetof(struct mckfd, ioctl_cb),
 .mckfd_mmap_cb_offset = __builtin_offsetof(struct mckfd, mmap_cb),
 .mckfd_close_cb_offset = __builtin_offsetof(struct mckfd, close_cb),
 .mckfd_fcntl_cb_offset = __builtin_offsetof(struct mckfd, fcntl_cb),
};
struct f03_perf_entry_ops_v1 {
 syscall_copy_from_user_fn_t copy_from_fn;
 perf_attr_freq_fn_t attr_freq_fn;
 perf_open_event_alloc_fn_t event_alloc_fn;
 perf_counter_alloc_fn_t counter_alloc_fn;
 perf_open_syscall_fn_t syscall_fn;
 syscall_policy_alloc_fn_t mckfd_alloc_fn;
 syscall_mckfd_long_fn_t read_fn;
 syscall_mckfd_int_fn_t ioctl_fn;
 syscall_mckfd_long_fn_t mmap_fn;
 syscall_mckfd_int_fn_t close_fn;
 syscall_mckfd_int_fn_t fcntl_fn;
 syscall_mckfd_lock_fn_t lock_fn;
 syscall_mckfd_unlock_fn_t unlock_fn;
};
const struct f03_perf_entry_ops_v1 f03_perf_entry_ops_v1 = {
 .copy_from_fn = syscall_copy_from_user_bridge,
 .attr_freq_fn = perf_event_open_attr_freq_bridge,
 .event_alloc_fn = perf_event_open_alloc_event_bridge,
 .counter_alloc_fn = perf_event_open_counter_alloc_bridge,
 .syscall_fn = perf_event_open_do_syscall_bridge,
 .mckfd_alloc_fn = perf_event_alloc_kmalloc_bridge,
 .read_fn = perf_read,
 .ioctl_fn = perf_ioctl,
 .mmap_fn = perf_mmap,
 .close_fn = perf_close,
 .fcntl_fn = perf_fcntl,
 .lock_fn = syscall_mckfd_lock_bridge,
 .unlock_fn = syscall_mckfd_unlock_bridge,
};

#define sys_perf_event_open original_sys_perf_event_open
long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx)
{
	struct syscall_request request IHK_DMA_ALIGN;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct perf_event_attr *arg0 = (void *)ihk_mc_syscall_arg0(ctx);
	int pid = ihk_mc_syscall_arg1(ctx);
	int cpu = ihk_mc_syscall_arg2(ctx);
	int group_fd = ihk_mc_syscall_arg3(ctx);
	unsigned long flags = ihk_mc_syscall_arg4(ctx);
	struct perf_event_attr attr_user;

#ifndef ENABLE_PERF
	return perf_event_open_disabled_body_result();
#endif // ENABLE_PERF

	return perf_event_open_entry_body_result(&request, thread, proc,
			&attr_user, (unsigned long)arg0,
			sizeof(struct perf_event_attr),
			__builtin_offsetof(struct perf_event_attr, type),
			__builtin_offsetof(struct perf_event_attr, read_format),
			__builtin_offsetof(struct perf_event_attr, sample_period),
			pid, cpu, group_fd, flags, ihk_mc_get_processor_id(),
			PERF_TYPE_RAW, PERF_TYPE_HARDWARE, PERF_TYPE_HW_CACHE,
			PERF_FORMAT_TOTAL_TIME_ENABLED |
			PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID,
			1UL << 63, __NR_perf_event_open, sizeof(struct mckfd),
			IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct mc_perf_event, pid),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct process, mckfd),
			__builtin_offsetof(struct mckfd, next),
			__builtin_offsetof(struct mckfd, fd),
			__builtin_offsetof(struct mckfd, data),
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, nr_siblings),
			__builtin_offsetof(struct mc_perf_event, pmc_status),
			__builtin_offsetof(struct thread, pmc_alloc_map),
			__builtin_offsetof(struct process, mckfd_lock),
			__builtin_offsetof(struct mckfd, sig_no),
			__builtin_offsetof(struct mckfd, read_cb),
			__builtin_offsetof(struct mckfd, ioctl_cb),
			__builtin_offsetof(struct mckfd, mmap_cb),
			__builtin_offsetof(struct mckfd, close_cb),
			__builtin_offsetof(struct mckfd, fcntl_cb),
			syscall_copy_from_user_bridge,
			perf_event_open_attr_freq_bridge,
			perf_event_open_alloc_event_bridge,
			perf_event_open_counter_alloc_bridge,
			perf_event_open_do_syscall_bridge,
			perf_event_alloc_kmalloc_bridge,
			perf_read, perf_ioctl, perf_mmap, perf_close, perf_fcntl,
			syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge);
}

#undef sys_perf_event_open
const unsigned long f03_perf_entry_fixture_C_ABI[56]={
sizeof(struct f03_perf_entry_layout_v1),
__alignof__(struct f03_perf_entry_layout_v1),
__builtin_offsetof(struct f03_perf_entry_layout_v1,raw_type),
__builtin_offsetof(struct f03_perf_entry_layout_v1,hardware_type),
__builtin_offsetof(struct f03_perf_entry_layout_v1,hw_cache_type),
__builtin_offsetof(struct f03_perf_entry_layout_v1,unsupported_read_format_mask),
__builtin_offsetof(struct f03_perf_entry_layout_v1,sample_period_sign_bit),
__builtin_offsetof(struct f03_perf_entry_layout_v1,perf_event_open_nr),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_size),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_alloc_flags),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_pid_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_counter_id_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,proc_mckfd_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_next_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_fd_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_data_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_group_leader_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_sibling_list_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_group_entry_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_nr_siblings_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,event_pmc_status_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,thread_pmc_alloc_map_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,proc_mckfd_lock_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_sig_no_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_read_cb_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_ioctl_cb_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_mmap_cb_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_close_cb_offset),
__builtin_offsetof(struct f03_perf_entry_layout_v1,mckfd_fcntl_cb_offset),
sizeof(struct f03_perf_entry_ops_v1),
__alignof__(struct f03_perf_entry_ops_v1),
__builtin_offsetof(struct f03_perf_entry_ops_v1,copy_from_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,attr_freq_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,event_alloc_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,counter_alloc_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,syscall_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,mckfd_alloc_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,read_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,ioctl_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,mmap_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,close_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,fcntl_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,lock_fn),
__builtin_offsetof(struct f03_perf_entry_ops_v1,unlock_fn),
sizeof(struct perf_event_attr),
__alignof__(struct perf_event_attr),
sizeof(struct syscall_request),
__alignof__(struct syscall_request),
sizeof(struct cpu_local_var),
__alignof__(struct cpu_local_var),
__builtin_offsetof(struct cpu_local_var,current),
sizeof(struct thread),
__alignof__(struct thread),
__builtin_offsetof(struct thread,proc),
sizeof(struct process),
__alignof__(struct process)
};
