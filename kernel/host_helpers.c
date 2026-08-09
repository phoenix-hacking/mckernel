/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <affinity.h>
#include <host_helpers.h>
#include <ihk/ihk_monitor.h>
#include <ihk/mm.h>
#include <ihk/perfctr.h>
#include <ikc/master.h>
#include <mman.h>
#include <object_helpers.h>
#include <process.h>
#include <string.h>
#include <syscall.h>

#ifndef MCKERNEL_RUST_HOST_HELPERS

struct host_mcctrl_signal {
	int cond;
	int sig;
	int pid;
	int tid;
	unsigned char info[128];
};

int host_ikc_packet_send_result(void *channel, struct ikc_scd_packet *packet,
				host_ikc_packet_send_fn_t send_fn)
{
	if (!packet || !send_fn)
		return -EINVAL;

	send_fn(channel, packet);
	return 0;
}

int host_ikc_connect_result(struct ihk_ikc_connect_param *param,
			    host_ikc_connect_fn_t connect_fn)
{
	if (!connect_fn)
		return -EINVAL;

	return connect_fn(param);
}

int host_delay_result(unsigned long usec, host_delay_fn_t delay_fn)
{
	if (!delay_fn)
		return -EINVAL;

	delay_fn(usec);
	return 0;
}

int host_set_current_ikc2linux_result(
		void *channel,
		host_set_current_ikc2linux_fn_t set_current_fn)
{
	if (!set_current_fn)
		return -EINVAL;

	set_current_fn(channel);
	return 0;
}

int host_ikc_set_regular_channel_result(
		void *channel, int cpu,
		host_ikc_set_regular_channel_fn_t set_regular_fn)
{
	if (!set_regular_fn)
		return -EINVAL;

	set_regular_fn(channel, cpu);
	return 0;
}

int host_panic_result(host_panic_fn_t panic_fn)
{
	if (!panic_fn)
		return -EINVAL;

	panic_fn();
	return 0;
}

int host_init_ikc_log_result(int event, host_init_ikc_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(event);
	return 0;
}

void *host_current_ptr_result(host_current_ptr_fn_t current_fn)
{
	if (!current_fn)
		return NULL;

	return current_fn();
}

int host_monitor_status_result(int cpu,
			       host_monitor_status_fn_t monitor_status_fn)
{
	if (!monitor_status_fn)
		return -EINVAL;

	return monitor_status_fn(cpu);
}

int host_tofu_finalize_result(host_tofu_finalize_fn_t tofu_finalize_fn)
{
	if (!tofu_finalize_fn)
		return -EINVAL;

	tofu_finalize_fn();
	return 0;
}

int host_prepare_process_log_result(int event, unsigned long arg0,
				    unsigned long arg1, unsigned long arg2,
				    host_prepare_process_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(event, arg0, arg1, arg2);
	return 0;
}

int host_prepare_ranges_log_result(int event, unsigned long arg0,
				   unsigned long arg1, unsigned long arg2,
				   host_prepare_ranges_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(event, arg0, arg1, arg2);
	return 0;
}

int host_prepare_args_log_result(int event, unsigned long arg0,
				 unsigned long arg1, unsigned long arg2,
				 host_prepare_args_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(event, arg0, arg1, arg2);
	return 0;
}

int host_prepare_process_result(unsigned long rphys,
				host_prepare_process_fn_t prepare_fn)
{
	if (!prepare_fn)
		return -EINVAL;

	return prepare_fn(rphys);
}

int host_prepare_ranges_result(void *thread, struct program_load_desc *pn,
			       struct program_load_desc *p, unsigned long attr,
			       char *args, int args_len, char *envs,
			       int envs_len, host_prepare_ranges_fn_t ranges_fn)
{
	if (!ranges_fn)
		return -EINVAL;

	return ranges_fn(thread, pn, p, attr, args, args_len, envs, envs_len);
}

int host_cleanup_process_result(int pid, host_cleanup_process_fn_t cleanup_fn)
{
	if (!cleanup_fn)
		return -EINVAL;

	return cleanup_fn(pid);
}

int host_cleanup_fd_result(int pid, int fd, host_cleanup_fd_fn_t cleanup_fn)
{
	if (!cleanup_fn)
		return -EINVAL;

	return cleanup_fn(pid, fd);
}

void *host_map_virtual_result(unsigned long phys, int npages, int attr,
			      host_map_virtual_fn_t map_virtual_fn)
{
	if (!map_virtual_fn)
		return NULL;

	return map_virtual_fn(phys, npages, attr);
}

unsigned long host_map_memory_result(void *os, unsigned long phys,
				     unsigned long size,
				     host_map_memory_fn_t map_memory_fn)
{
	if (!map_memory_fn)
		return 0;

	return map_memory_fn(os, phys, size);
}

void *host_prepare_map_virtual_result(unsigned long phys, int npages,
				      unsigned long attr,
				      host_prepare_map_virtual_fn_t map_virtual_fn)
{
	if (!map_virtual_fn)
		return NULL;

	return map_virtual_fn(phys, npages, attr);
}

int host_unmap_virtual_result(void *addr, int npages,
			      host_unmap_virtual_fn_t unmap_virtual_fn)
{
	if (!unmap_virtual_fn)
		return -EINVAL;

	unmap_virtual_fn(addr, npages);
	return 0;
}

int host_unmap_memory_result(void *os, unsigned long phys,
			     unsigned long size,
			     host_unmap_memory_fn_t unmap_memory_fn)
{
	if (!unmap_memory_fn)
		return -EINVAL;

	unmap_memory_fn(os, phys, size);
	return 0;
}

int host_prepare_add_range_result(void *vm, unsigned long start,
				  unsigned long end, unsigned long phys,
				  unsigned long flag, int pgshift,
				  void **rangep,
				  host_prepare_add_range_fn_t add_range_fn)
{
	if (!add_range_fn)
		return -EINVAL;

	return add_range_fn(vm, start, end, phys, flag, pgshift, rangep);
}

void *host_prepare_alloc_pages_user_result(
		int npages, unsigned long flags, unsigned long virt_addr,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn)
{
	if (!alloc_pages_fn)
		return NULL;

	return alloc_pages_fn(npages, flags, virt_addr);
}

int host_prepare_free_pages_user_result(
		void *addr, int npages,
		host_prepare_free_pages_user_fn_t free_pages_fn)
{
	if (!free_pages_fn)
		return -EINVAL;

	free_pages_fn(addr, npages);
	return 0;
}

unsigned long host_virt_to_phys_result(void *addr,
				       host_virt_to_phys_fn_t virt_to_phys_fn)
{
	if (!virt_to_phys_fn)
		return 0;

	return virt_to_phys_fn(addr);
}

unsigned long host_arch_vrflag_to_ptattr_result(
		unsigned long flag, unsigned long fault, void *ptep,
		host_arch_vrflag_to_ptattr_fn_t attr_fn)
{
	if (!attr_fn)
		return 0;

	return attr_fn(flag, fault, ptep);
}

int host_pt_set_range_result(void *page_table, void *vm,
			     unsigned long start, unsigned long end,
			     unsigned long phys, unsigned long attr, int pgshift,
			     void *range, int flags,
			     host_pt_set_range_fn_t pt_set_range_fn)
{
	if (!pt_set_range_fn)
		return -EINVAL;

	return pt_set_range_fn(page_table, vm, start, end, phys, attr,
			pgshift, range, flags);
}

int host_modify_user_context_result(void *uctx, int reg, unsigned long value,
				    host_modify_user_context_fn_t modify_fn)
{
	if (!modify_fn)
		return -EINVAL;

	modify_fn(uctx, reg, value);
	return 0;
}

void *host_prepare_alloc_result(unsigned long size, unsigned long flags,
				host_alloc_fn_t alloc_fn)
{
	if (!alloc_fn)
		return NULL;

	return alloc_fn(size, flags);
}

int host_prepare_free_result(void *ptr, host_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	free_fn(ptr);
	return 0;
}

int host_prepare_copy_long_result(void *dst, const void *src,
				  unsigned long size, host_copy_long_fn_t copy_fn)
{
	if (!copy_fn)
		return -EINVAL;

	copy_fn(dst, src, size);
	return 0;
}

void *host_create_thread_result(unsigned long entry, unsigned long *cpu_set,
				unsigned long cpu_set_size,
				host_create_thread_fn_t create_fn)
{
	if (!create_fn)
		return NULL;

	return create_fn(entry, cpu_set, cpu_set_size);
}

int host_destroy_thread_result(void *thread, host_destroy_thread_fn_t destroy_fn)
{
	if (!destroy_fn)
		return -EINVAL;

	destroy_fn(thread);
	return 0;
}

int host_nr_numa_nodes_result(host_nr_numa_nodes_fn_t nr_numa_nodes_fn)
{
	if (!nr_numa_nodes_fn)
		return -EINVAL;

	return nr_numa_nodes_fn();
}

int host_flush_tlb_result(host_flush_tlb_fn_t flush_tlb_fn)
{
	if (!flush_tlb_fn)
		return -EINVAL;

	flush_tlb_fn();
	return 0;
}

int host_arch_map_vdso_result(void *vm,
			      host_arch_map_vdso_fn_t arch_map_vdso_fn)
{
	if (!arch_map_vdso_fn)
		return -EINVAL;

	return arch_map_vdso_fn(vm);
}

int host_init_process_stack_result(
		void *thread, struct program_load_desc *pn,
		unsigned long at_base, int argc, char **argv, int envc,
		char **env, host_init_process_stack_fn_t init_stack_fn)
{
	if (!init_stack_fn)
		return -EINVAL;

	return init_stack_fn(thread, pn, at_base, argc, argv, envc, env);
}

void *host_thread_proc_result(void *thread,
			      host_thread_proc_fn_t thread_proc_fn)
{
	if (!thread_proc_fn)
		return NULL;

	return thread_proc_fn(thread);
}

int host_current_cpu_result(host_current_cpu_fn_t current_cpu_fn)
{
	if (!current_cpu_fn)
		return -EINVAL;

	return current_cpu_fn();
}

int host_thread_cpu_allowed_result(void *thread, int cpuid,
				   host_thread_cpu_allowed_fn_t cpu_allowed_fn)
{
	if (!cpu_allowed_fn)
		return -EINVAL;

	return cpu_allowed_fn(thread, cpuid);
}

int host_thread_obtain_cpuid_result(
		void *thread, host_thread_obtain_cpuid_fn_t obtain_cpuid_fn)
{
	if (!obtain_cpuid_fn)
		return -EINVAL;

	return obtain_cpuid_fn(thread);
}

int host_proc_pid_result(void *proc, host_proc_pid_fn_t proc_pid_fn)
{
	if (!proc_pid_fn)
		return -EINVAL;

	return proc_pid_fn(proc);
}

unsigned long host_thread_reg_result(void *thread,
				     host_thread_reg_fn_t thread_reg_fn)
{
	if (!thread_reg_fn)
		return 0;

	return thread_reg_fn(thread);
}

int host_schedule_invalid_log_result(
		void *thread, host_schedule_invalid_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(thread);
	return 0;
}

int host_schedule_received_log_result(
		void *thread, int pid, unsigned long pc, unsigned long sp,
		int cpuid, host_schedule_received_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(thread, pid, pc, sp, cpuid);
	return 0;
}

int host_schedule_no_cpu_log_result(host_schedule_no_cpu_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn();
	return 0;
}

int host_thread_set_tid_result(void *thread, int tid,
			       host_thread_set_tid_fn_t set_tid_fn)
{
	if (!set_tid_fn)
		return -EINVAL;

	set_tid_fn(thread, tid);
	return 0;
}

int host_status_set_result(void *object, int status,
			   host_status_set_fn_t status_set_fn)
{
	if (!status_set_fn)
		return -EINVAL;

	status_set_fn(object, status);
	return 0;
}

int host_chain_thread_result(void *thread,
			     host_chain_thread_fn_t chain_thread_fn)
{
	if (!chain_thread_fn)
		return -EINVAL;

	chain_thread_fn(thread);
	return 0;
}

int host_chain_process_result(void *proc,
			      host_chain_process_fn_t chain_process_fn)
{
	if (!chain_process_fn)
		return -EINVAL;

	chain_process_fn(proc);
	return 0;
}

int host_runq_add_thread_result(void *thread, int cpuid,
				host_runq_add_thread_fn_t runq_add_fn)
{
	if (!runq_add_fn)
		return -EINVAL;

	runq_add_fn(thread, cpuid);
	return 0;
}

int host_schedule_queued_log_result(
		int pid, int tid, int cpuid, int status,
		host_schedule_queued_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(pid, tid, cpuid, status);
	return 0;
}

int host_init_ack_log_result(host_init_ack_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn();
	return 0;
}

int host_schedule_process_log_result(struct ikc_scd_packet *request,
				     host_schedule_process_log_fn_t log_fn)
{
	if (!request || !log_fn)
		return -EINVAL;

	log_fn(request->arg);
	return 0;
}

int host_thread_profile_enabled_result(
		void *thread,
		host_thread_profile_enabled_fn_t profile_enabled_fn)
{
	if (!profile_enabled_fn)
		return -EINVAL;

	return profile_enabled_fn(thread);
}

unsigned long host_timestamp_result(host_timestamp_fn_t timestamp_fn)
{
	if (!timestamp_fn)
		return 0;

	return timestamp_fn();
}

int host_preempt_result(host_preempt_fn_t preempt_fn)
{
	if (!preempt_fn)
		return -EINVAL;

	preempt_fn();
	return 0;
}

int host_remote_page_fault_process_result(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason,
		host_remote_page_fault_fn_t page_fault_fn)
{
	if (!page_fault_fn)
		return -EINVAL;

	page_fault_fn(thread, fault_address, fault_reason);
	return 0;
}

int host_profile_event_result(int event, unsigned long delta,
			      host_profile_event_fn_t profile_event_fn)
{
	if (!profile_event_fn)
		return -EINVAL;

	profile_event_fn(event, delta);
	return 0;
}

int host_remote_page_fault_log_result(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason,
		host_remote_page_fault_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(thread, fault_address, fault_reason);
	return 0;
}

void *host_alloc_result(unsigned long size, unsigned long flags,
			host_alloc_fn_t alloc_fn)
{
	if (!alloc_fn)
		return NULL;

	return alloc_fn(size, flags);
}

int host_packet_copy_result(void *dst, struct ikc_scd_packet *src,
			    unsigned long size, host_packet_copy_fn_t copy_fn)
{
	if (!copy_fn)
		return -EINVAL;

	copy_fn(dst, src, size);
	return 0;
}

int host_remote_page_fault_defer_result(
		void *thread, void *arg, host_backlog_fn_t backlog_fn,
		host_remote_page_fault_defer_fn_t defer_fn)
{
	if (!defer_fn || !backlog_fn)
		return -EINVAL;

	defer_fn(thread, arg, backlog_fn);
	return 0;
}

int host_sched_wakeup_result(void *thread, int valid_states,
			     host_sched_wakeup_fn_t wakeup_fn)
{
	if (!wakeup_fn)
		return -EINVAL;

	return wakeup_fn(thread, valid_states);
}

int host_remote_page_fault_missing_log_result(
		int tid, host_remote_page_fault_missing_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(tid);
	return 0;
}

int host_cpu_rw_register_result(void *desc, int op,
				host_cpu_rw_register_fn_t rw_register_fn)
{
	if (!rw_register_fn)
		return -EINVAL;

	return rw_register_fn(desc, op);
}

int host_cleanup_process_log_result(
		int pid, unsigned long thread_arg,
		host_cleanup_process_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(pid, thread_arg);
	return 0;
}

int host_terminate_host_result(int pid, void *thread,
			       host_terminate_host_fn_t terminate_fn)
{
	if (!terminate_fn)
		return -EINVAL;

	terminate_fn(pid, thread);
	return 0;
}

int host_cleanup_fd_log_result(int pid, unsigned long fd, int err,
			       host_cleanup_fd_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(pid, fd, err);
	return 0;
}

unsigned long host_do_kill_result(
		int pid, int tid, int sig, void *info,
		host_do_kill_fn_t do_kill_fn)
{
	if (!do_kill_fn)
		return (unsigned long)-EINVAL;

	return do_kill_fn(pid, tid, sig, info);
}

int host_send_signal_log_result(int pid, int tid, int sig, int rc,
				host_send_signal_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(pid, tid, sig, rc);
	return 0;
}

void *host_find_thread_result(int pid, int tid,
			      host_find_thread_fn_t find_thread_fn)
{
	if (!find_thread_fn)
		return NULL;

	return find_thread_fn(pid, tid);
}

int host_wakeup_thread_result(void *thread,
			      host_wakeup_thread_fn_t wakeup_fn)
{
	if (!wakeup_fn)
		return -EINVAL;

	wakeup_fn(thread);
	return 0;
}

int host_thread_unlock_result(void *thread,
			      host_thread_unlock_fn_t unlock_fn)
{
	if (!unlock_fn)
		return -EINVAL;

	unlock_fn(thread);
	return 0;
}

int host_wake_syscall_log_result(int tid, int found,
				 host_wake_syscall_log_fn_t log_fn)
{
	if (!log_fn)
		return -EINVAL;

	log_fn(tid, found);
	return 0;
}

int host_debug_log_result(unsigned long code,
			  host_debug_log_fn_t debug_fn)
{
	if (!debug_fn)
		return -EINVAL;

	debug_fn(code);
	return 0;
}

int host_debug_log_print_result(unsigned long code,
				host_debug_log_print_fn_t print_fn)
{
	if (!print_fn)
		return -EINVAL;

	print_fn(code);
	return 0;
}

int host_perf_init_raw_result(int counter, unsigned int config, int mode,
			      host_perf_init_raw_fn_t init_raw_fn)
{
	if (!init_raw_fn)
		return -EINVAL;

	return init_raw_fn(counter, config, mode);
}

int host_perf_stop_result(unsigned long counter_mask, int flags,
			  host_perf_stop_fn_t stop_fn)
{
	if (!stop_fn)
		return -EINVAL;

	return stop_fn(counter_mask, flags);
}

int host_perf_reset_result(int counter, host_perf_reset_fn_t reset_fn)
{
	if (!reset_fn)
		return -EINVAL;

	return reset_fn(counter);
}

int host_perf_start_result(unsigned long counter_mask,
			   host_perf_start_fn_t start_fn)
{
	if (!start_fn)
		return -EINVAL;

	return start_fn(counter_mask);
}

unsigned long host_perf_read_result(int counter, host_perf_read_fn_t read_fn)
{
	if (!read_fn)
		return 0;

	return read_fn(counter);
}

int host_perf_unexpected_result(host_perf_unexpected_fn_t unexpected_fn)
{
	if (!unexpected_fn)
		return -EINVAL;

	unexpected_fn();
	return 0;
}

static unsigned long host_prepare_desc_bytes(int nsections)
{
	return sizeof(struct program_load_desc) +
		sizeof(struct program_image_section) * (unsigned long)nsections;
}

static void host_prepare_set_mask_bit(unsigned long *mask, int bit)
{
	mask[bit / BITS_PER_LONG] |= 1UL << (bit % BITS_PER_LONG);
}

static int host_prepare_test_mask_bit(const unsigned long *mask, int bit)
{
	return (mask[bit / BITS_PER_LONG] & (1UL << (bit % BITS_PER_LONG))) != 0;
}

static int host_prepare_publish_numa_bind(
		struct process_vm *vm, struct program_load_desc *pn,
		int mpol_bind, int nr_numa_nodes,
		host_prepare_process_log_fn_t log_fn)
{
	int bit;

	memset(&vm->numa_mask, 0, sizeof(vm->numa_mask));
	for (bit = 0; bit < (int)(sizeof(pn->mpol_bind_mask) * BITS_PER_BYTE);
	     bit++) {
		if (!(pn->mpol_bind_mask & (1UL << bit)))
			continue;
		if (bit >= nr_numa_nodes) {
			if (log_fn)
				host_prepare_process_log_result(
					HOST_PREPARE_LOG_NUMA_BIND_ERROR,
					bit, 0, 0, log_fn);
			return -EINVAL;
		}
		host_prepare_set_mask_bit(&vm->numa_mask[0], bit);
	}
	vm->numa_mem_policy = mpol_bind;
	return 0;
}

static int host_prepare_publish_numa_policy(
		struct process_vm *vm, struct program_load_desc *pn,
		int nr_numa_nodes, host_prepare_process_log_fn_t log_fn)
{
	int bit;

	vm->numa_mem_policy = pn->mpol_mode;
	memset(&vm->numa_mask, 0, sizeof(vm->numa_mask));
	for (bit = 0; bit < PLD_PROCESS_NUMA_MASK_BITS; bit++) {
		if (!host_prepare_test_mask_bit(pn->mpol_nodemask, bit))
			continue;
		if (bit >= nr_numa_nodes) {
			if (log_fn)
				host_prepare_process_log_result(
					HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR,
					bit, 0, 0, log_fn);
			return -EINVAL;
		}
		host_prepare_set_mask_bit(&vm->numa_mask[0], bit);
	}
	if (log_fn)
		host_prepare_process_log_result(HOST_PREPARE_LOG_NUMA_POLICY,
						vm->numa_mem_policy,
						vm->numa_mask[0], 0,
						log_fn);
	return 0;
}

static int host_prepare_publish_process_state(
		struct thread *thread, struct program_load_desc *pn,
		unsigned long user_end, unsigned long ld_task_unmapped_base,
		int sigchld, int mpol_max, int mpol_bind,
		host_nr_numa_nodes_fn_t nr_numa_nodes_fn,
		host_tofu_finalize_fn_t tofu_finalize_fn,
		host_prepare_process_log_fn_t log_fn)
{
	struct process *proc;
	struct process_vm *vm;
	int rc;

	proc = thread->proc;
	vm = thread->vm;
	if (!proc || !vm || !vm->address_space)
		return -EINVAL;

	memcpy(thread->pthread_routine, "[main]", sizeof("[main]"));
	proc->pid = pn->pid;
	proc->vm->address_space->pids[0] = pn->pid;
	proc->pgid = pn->pgid;
	proc->ruid = pn->cred[0];
	proc->euid = pn->cred[1];
	proc->suid = pn->cred[2];
	proc->fsuid = pn->cred[3];
	proc->rgid = pn->cred[4];
	proc->egid = pn->cred[5];
	proc->sgid = pn->cred[6];
	proc->fsgid = pn->cred[7];
	proc->termsig = sigchld;
	proc->mpol_flags = pn->mpol_flags;
	proc->mpol_threshold = pn->mpol_threshold;
	proc->thp_disable = pn->thp_disable;
	proc->nr_processes = pn->nr_processes;
	proc->process_rank = pn->process_rank;
	proc->heap_extension = pn->heap_extension;

	if (pn->mpol_bind_mask) {
		if (!nr_numa_nodes_fn)
			return -EINVAL;
		rc = host_prepare_publish_numa_bind(vm, pn, mpol_bind,
				host_nr_numa_nodes_result(nr_numa_nodes_fn),
				log_fn);
		if (rc)
			return rc;
	} else if (pn->mpol_mode != mpol_max) {
		if (!nr_numa_nodes_fn)
			return -EINVAL;
		rc = host_prepare_publish_numa_policy(vm, pn,
				host_nr_numa_nodes_result(nr_numa_nodes_fn),
				log_fn);
		if (rc)
			return rc;
	}

	proc->enable_uti = pn->enable_uti;
	proc->uti_thread_rank = pn->uti_thread_rank;
	proc->uti_use_last_cpu = pn->uti_use_last_cpu;
	proc->straight_map = pn->straight_map;
	proc->straight_map_threshold = pn->straight_map_threshold;
#ifdef ENABLE_TOFU
	proc->enable_tofu = pn->enable_tofu;
	if (proc->enable_tofu && tofu_finalize_fn)
		host_tofu_finalize_result(tofu_finalize_fn);
#else
	(void)tofu_finalize_fn;
#endif
	proc->mcexec_flags = pn->mcexec_flags;
	if (log_fn)
		host_prepare_process_log_result(HOST_PREPARE_LOG_PID_FLAGS,
						proc->pid, proc->mcexec_flags,
						0, log_fn);

	memcpy(proc->rlimit, pn->rlimit, sizeof(struct rlimit) * MCK_RLIM_MAX);
	if (log_fn)
		host_prepare_process_log_result(HOST_PREPARE_LOG_RLIMIT,
				proc->rlimit[MCK_RLIMIT_STACK].rlim_cur,
				proc->rlimit[MCK_RLIMIT_STACK].rlim_max,
				pn->stack_premap, log_fn);

#ifdef PROFILE_ENABLE
	proc->profile = pn->profile;
	thread->profile = pn->profile;
#endif

	vm->region.user_start = pn->user_start;
	vm->region.user_end = pn->user_end;
	if (vm->region.user_end > user_end)
		vm->region.user_end = user_end;
	vm->region.map_start = vm->region.map_end = ld_task_unmapped_base;

	return 0;
}

int host_prepare_process_body_result(
		unsigned long rphys, int num_processors, unsigned long attr,
		unsigned long page_size, unsigned long alloc_flags,
		unsigned long user_end, unsigned long ld_task_unmapped_base,
		int sigchld, int mpol_max, int mpol_bind,
		host_monitor_status_fn_t monitor_status_fn,
		host_map_memory_fn_t map_memory_fn,
		host_prepare_map_virtual_fn_t map_virtual_fn,
		host_unmap_virtual_fn_t unmap_virtual_fn,
		host_unmap_memory_fn_t unmap_memory_fn,
		host_alloc_fn_t alloc_fn, host_free_fn_t free_fn,
		host_copy_long_fn_t copy_long_fn,
		host_create_thread_fn_t create_thread_fn,
		host_destroy_thread_fn_t destroy_thread_fn,
		host_prepare_ranges_fn_t prepare_ranges_fn,
		host_nr_numa_nodes_fn_t nr_numa_nodes_fn,
		host_flush_tlb_fn_t flush_tlb_fn,
		host_tofu_finalize_fn_t tofu_finalize_fn,
		host_prepare_process_log_fn_t log_fn)
{
	unsigned long phys, sz, clone_sz;
	struct program_load_desc *p, *pn;
	int npages, n, i;
	struct thread *thread;
	int error;

	if (!monitor_status_fn || !map_memory_fn || !map_virtual_fn ||
	    !unmap_virtual_fn || !unmap_memory_fn || !alloc_fn || !free_fn ||
	    !copy_long_fn || !create_thread_fn || !destroy_thread_fn ||
	    !prepare_ranges_fn || !flush_tlb_fn || !page_size)
		return -EINVAL;

	for (i = 0; i < num_processors; i++) {
		int status = host_monitor_status_result(i, monitor_status_fn);

		if (status == IHK_OS_MONITOR_KERNEL_FREEZING ||
		    status == IHK_OS_MONITOR_KERNEL_FROZEN)
			return -EAGAIN;
	}

	sz = sizeof(struct program_load_desc)
		+ sizeof(struct program_image_section) * 16;
	npages = ((rphys + sz - 1) / page_size) - (rphys / page_size) + 1;

	phys = host_map_memory_result(NULL, rphys, sz, map_memory_fn);
	p = host_prepare_map_virtual_result(phys, npages, attr,
					    map_virtual_fn);
	if (!p) {
		host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
		return -ENOMEM;
	}

	if (p->magic != PLD_MAGIC) {
		if (log_fn)
			host_prepare_process_log_result(
				HOST_PREPARE_LOG_BROKEN_DESC, 0, 0, 0,
				log_fn);
		host_unmap_virtual_result(p, npages, unmap_virtual_fn);
		host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
		return -EFAULT;
	}

	n = p->num_sections;
	if (n > 16 || 0 >= n) {
		if (log_fn)
			host_prepare_process_log_result(
				HOST_PREPARE_LOG_INVALID_SECTIONS, n, 0, 0,
				log_fn);
		return -ENOMEM;
	}
	if (log_fn)
		host_prepare_process_log_result(HOST_PREPARE_LOG_NUM_SECTIONS,
						n, 0, 0, log_fn);

	clone_sz = host_prepare_desc_bytes(n);
	pn = host_prepare_alloc_result(clone_sz, alloc_flags, alloc_fn);
	if (!pn) {
		host_unmap_virtual_result(p, npages, unmap_virtual_fn);
		host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
		return -ENOMEM;
	}
	host_prepare_copy_long_result(pn, p, clone_sz, copy_long_fn);

	thread = host_create_thread_result(p->entry, (unsigned long *)&p->cpu_set,
					   sizeof(p->cpu_set),
					   create_thread_fn);
	if (!thread) {
		host_prepare_free_result(pn, free_fn);
		host_unmap_virtual_result(p, npages, unmap_virtual_fn);
		host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
		return -ENOMEM;
	}

	error = host_prepare_publish_process_state(thread, pn, user_end,
			ld_task_unmapped_base, sigchld, mpol_max, mpol_bind,
			nr_numa_nodes_fn, tofu_finalize_fn, log_fn);
	if (error)
		return error;

	error = host_prepare_ranges_result(thread, pn, p, attr, NULL, 0, NULL,
					   0, prepare_ranges_fn);
	if (error) {
		if (log_fn)
			host_prepare_process_log_result(
				HOST_PREPARE_LOG_PREPARE_ERROR, error, 0, 0,
				log_fn);
		host_prepare_free_result(pn, free_fn);
		host_unmap_virtual_result(p, npages, unmap_virtual_fn);
		host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
		host_destroy_thread_result(thread, destroy_thread_fn);
		return -ENOMEM;
	}

	if (log_fn)
		host_prepare_process_log_result(
			HOST_PREPARE_LOG_NEW_PROCESS,
			(unsigned long)thread->proc,
			thread->proc ? thread->proc->pid : 0,
			thread->vm ? (unsigned long)thread->vm->address_space : 0,
			log_fn);

	host_prepare_free_result(pn, free_fn);
	host_unmap_virtual_result(p, npages, unmap_virtual_fn);
	host_unmap_memory_result(NULL, phys, sz, unmap_memory_fn);
	host_flush_tlb_result(flush_tlb_fn);

	return 0;
}

int host_prepare_ranges_sections_result(
		void *thread_arg, struct program_load_desc *pn,
		struct program_load_desc *p, unsigned long *at_basep,
		unsigned long page_size, unsigned long page_mask,
		unsigned long large_page_size, unsigned long large_page_mask,
		unsigned long task_unmapped_base, int page_shift,
		int large_page_shift, unsigned long alloc_nowait,
		unsigned long alloc_user, unsigned long mpol_no_bss,
		unsigned long pf_populate, int user_context_pc_reg,
		host_prepare_add_range_fn_t add_range_fn,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn,
		host_prepare_free_pages_user_fn_t free_pages_fn,
		host_virt_to_phys_fn_t virt_to_phys_fn,
		host_arch_vrflag_to_ptattr_fn_t arch_vrflag_to_ptattr_fn,
		host_pt_set_range_fn_t pt_set_range_fn,
		host_modify_user_context_fn_t modify_context_fn,
		host_prepare_ranges_log_fn_t log_fn)
{
	struct thread *thread = thread_arg;
	struct process *proc;
	struct process_vm *vm;
	uintptr_t interp_obase = (uintptr_t)-1;
	uintptr_t interp_nbase = (uintptr_t)-1;
	unsigned long aout_base;
	int n, i;

	if (!thread || !pn || !p || !at_basep || !page_size ||
	    !add_range_fn || !alloc_pages_fn || !free_pages_fn ||
	    !virt_to_phys_fn || !arch_vrflag_to_ptattr_fn || !pt_set_range_fn)
		return -EINVAL;

	proc = thread->proc;
	if (!proc || !proc->vm || !proc->vm->address_space)
		return -EINVAL;
	vm = proc->vm;

	n = p->num_sections;
	vm->region.data_start = ~0UL;
	aout_base = pn->reloc ? vm->region.map_end : 0;

	for (i = 0; i < n; i++) {
		unsigned long ap_flags = 0;
		unsigned long s, e, up;
		unsigned long flags;
		void *up_v;
		void *range = NULL;
		int range_npages;
		unsigned long ptattr;
		int error;

		if (pn->sections[i].interp && interp_nbase == (uintptr_t)-1) {
			if (!pn->interp_align)
				return -EINVAL;
			interp_obase = pn->sections[i].vaddr;
			interp_obase -= interp_obase % pn->interp_align;
			interp_nbase = vm->region.map_end;
			interp_nbase = (interp_nbase + pn->interp_align - 1)
				& ~(pn->interp_align - 1);
		}

		if (pn->sections[i].interp) {
			pn->sections[i].vaddr -= interp_obase;
			pn->sections[i].vaddr += interp_nbase;
			p->sections[i].vaddr = pn->sections[i].vaddr;
		} else {
			pn->sections[i].vaddr += aout_base;
			p->sections[i].vaddr = pn->sections[i].vaddr;
		}

		s = pn->sections[i].vaddr & page_mask;
		e = (pn->sections[i].vaddr + pn->sections[i].len
		     + page_size - 1) & page_mask;
		range_npages = ((pn->sections[i].vaddr - s)
				+ pn->sections[i].filesz + page_size - 1)
			>> page_shift;
		flags = VR_NONE;
		flags |= PROT_TO_VR_FLAG(pn->sections[i].prot);
		flags |= VRFLAG_PROT_TO_MAXPROT(flags);
		flags |= VR_DEMAND_PAGING;

		if (i >= 1 && pn->sections[i].len >= pn->mpol_threshold &&
		    !(pn->mpol_flags & mpol_no_bss)) {
			ap_flags = alloc_user;
			flags |= VR_AP_USER;
			if (log_fn)
				host_prepare_ranges_log_result(
					HOST_PREPARE_RANGES_LOG_AP_USER, i,
					range_npages, 0, log_fn);
		}

		error = host_prepare_add_range_result(
				     vm, s, e, (unsigned long)-1, flags,
				     pn->sections[i].len > large_page_size ?
				     large_page_shift : page_shift, &range,
				     add_range_fn);
		if (error) {
			if (log_fn)
				host_prepare_ranges_log_result(
					HOST_PREPARE_RANGES_LOG_ADD_FAILED,
					i, error, 0, log_fn);
			return error;
		}
		if (!range)
			return -EINVAL;

		up_v = host_prepare_alloc_pages_user_result(
				range_npages, alloc_nowait | ap_flags, s,
				alloc_pages_fn);
		if (!up_v) {
			if (log_fn)
				host_prepare_ranges_log_result(
					HOST_PREPARE_RANGES_LOG_ALLOC_FAILED,
					i, 0, 0, log_fn);
			return -ENOMEM;
		}

		up = host_virt_to_phys_result(up_v, virt_to_phys_fn);
		ptattr = host_arch_vrflag_to_ptattr_result(
				((struct vm_range *)range)->flag,
				pf_populate, NULL, arch_vrflag_to_ptattr_fn);
		error = host_pt_set_range_result(vm->address_space->page_table, vm,
					((struct vm_range *)range)->start,
					((struct vm_range *)range)->start
					+ range_npages * page_size,
					up, ptattr,
					((struct vm_range *)range)->pgshift,
					range, 0, pt_set_range_fn);
		if (error) {
			if (log_fn)
				host_prepare_ranges_log_result(
					HOST_PREPARE_RANGES_LOG_PT_FAILED,
					i, error, 0, log_fn);
			host_prepare_free_pages_user_result(up_v, range_npages,
							    free_pages_fn);
			return error;
		}

		p->sections[i].remote_pa = up;
		if (pn->sections[i].interp) {
			vm->region.map_end = e;
		} else if (pn->sections[i].prot & PROT_EXEC) {
			vm->region.text_start = s;
			vm->region.text_end = e;
		} else {
			vm->region.data_start =
				s < vm->region.data_start ? s : vm->region.data_start;
			vm->region.data_end =
				e > vm->region.data_end ? e : vm->region.data_end;
		}

		if (aout_base)
			vm->region.map_end = e;
	}

	*at_basep = 0;
	if (interp_nbase != (uintptr_t)-1) {
		*at_basep = interp_nbase - interp_obase;
		pn->entry -= interp_obase;
		pn->entry += interp_nbase;
		p->entry = pn->entry;
		if (modify_context_fn)
			host_modify_user_context_result(thread->uctx,
					user_context_pc_reg, pn->entry,
					modify_context_fn);
	}

	if (aout_base) {
		pn->at_phdr += aout_base;
		pn->at_entry += aout_base;
	}

	vm->region.map_start = vm->region.map_end = task_unmapped_base;
	vm->region.brk_start = vm->region.brk_end =
		(vm->region.data_end + large_page_size - 1) & large_page_mask;

	if (vm->region.brk_start >= vm->region.map_start) {
		if (log_fn)
			host_prepare_ranges_log_result(
				HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE,
				vm->region.data_end, vm->region.map_start, 0,
				log_fn);
		return -ENOMEM;
	}

	vm->region.brk_end_allocated = vm->region.brk_end;
	return 0;
}

static int host_prepare_argenv_pages(unsigned long addr, unsigned long len,
				     unsigned long page_size, int page_shift)
{
	return (((addr & (page_size - 1)) + len + page_size - 1)
		>> page_shift);
}

int host_prepare_ranges_args_envs_result(
		void *thread_arg, struct program_load_desc *pn,
		struct program_load_desc *p, unsigned long attr,
		char *args, int args_len, char *envs, int envs_len,
		unsigned long at_base, unsigned long page_size,
		unsigned long page_mask, int page_shift,
		unsigned long alloc_nowait,
		host_prepare_add_range_fn_t add_range_fn,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn,
		host_prepare_free_pages_user_fn_t free_pages_fn,
		host_virt_to_phys_fn_t virt_to_phys_fn,
		host_map_memory_fn_t map_memory_fn,
		host_prepare_map_virtual_fn_t map_virtual_fn,
		host_unmap_virtual_fn_t unmap_virtual_fn,
		host_unmap_memory_fn_t unmap_memory_fn,
		host_copy_long_fn_t copy_long_fn,
		host_alloc_fn_t alloc_fn, host_free_fn_t free_fn,
		host_flush_tlb_fn_t flush_tlb_fn,
		host_arch_map_vdso_fn_t arch_map_vdso_fn,
		host_init_process_stack_fn_t init_stack_fn,
		host_prepare_args_log_fn_t log_fn)
{
	struct thread *thread = thread_arg;
	struct process *proc;
	struct process_vm *vm;
	struct address_space *as;
	char *args_envs, *args_envs_r;
	unsigned long args_envs_p, args_envs_rp = 0, envs_offset;
	unsigned long addr, end, flags, map_size;
	int args_envs_npages = 0;
	int argenv_page_count = 0;
	char **argv, **env;
	int argc, envc;
	int error, i;

	(void)page_mask;
	if (!thread || !pn || !p || !page_size || !add_range_fn ||
	    !alloc_pages_fn || !free_pages_fn || !virt_to_phys_fn ||
	    !map_memory_fn || !map_virtual_fn || !unmap_virtual_fn ||
	    !unmap_memory_fn || !copy_long_fn || !alloc_fn || !free_fn ||
	    !flush_tlb_fn || !init_stack_fn)
		return -EINVAL;

	proc = thread->proc;
	if (!proc || !proc->vm || !proc->vm->address_space)
		return -EINVAL;
	vm = proc->vm;
	as = vm->address_space;

	if (!args) {
		argenv_page_count += host_prepare_argenv_pages(
			(unsigned long)p->args, p->args_len, page_size,
			page_shift);
	} else {
		argenv_page_count += (args_len + page_size - 1) >> page_shift;
	}
	if (!envs) {
		argenv_page_count += host_prepare_argenv_pages(
			(unsigned long)p->envs, p->envs_len, page_size,
			page_shift);
	} else {
		argenv_page_count += (envs_len + page_size - 1) >> page_shift;
	}

	addr = vm->region.map_start - page_size * argenv_page_count;
	end = addr + page_size * argenv_page_count;
	args_envs = host_prepare_alloc_pages_user_result(
			argenv_page_count, alloc_nowait, ~0UL, alloc_pages_fn);
	if (!args_envs) {
		if (log_fn)
			host_prepare_args_log_result(
				HOST_PREPARE_ARGS_LOG_ALLOC_FAILED,
				argenv_page_count, 0, 0, log_fn);
		return -ENOMEM;
	}
	args_envs_p = host_virt_to_phys_result(args_envs, virt_to_phys_fn);

	flags = VR_PROT_READ | VR_PROT_WRITE | VR_PRIVATE;
	flags |= VRFLAG_PROT_TO_MAXPROT(flags);
	error = host_prepare_add_range_result(vm, addr, end, args_envs_p,
			flags, page_shift, NULL, add_range_fn);
	if (error) {
		host_prepare_free_pages_user_result(args_envs, argenv_page_count,
						    free_pages_fn);
		if (log_fn)
			host_prepare_args_log_result(
				HOST_PREPARE_ARGS_LOG_ADD_FAILED, error, 0, 0,
				log_fn);
		return error;
	}

	if (!args) {
		map_size = ((uintptr_t)p->args & (page_size - 1)) + p->args_len;
		args_envs_npages = (map_size + page_size - 1) >> page_shift;
		args_envs_rp = host_map_memory_result(
				NULL, (unsigned long)p->args, p->args_len,
				map_memory_fn);
		args_envs_r = host_prepare_map_virtual_result(
				args_envs_rp, args_envs_npages, attr,
				map_virtual_fn);
		if (!args_envs_r) {
			if (log_fn)
				host_prepare_args_log_result(
					HOST_PREPARE_ARGS_LOG_ARGS_MAP_FAILED,
					args_envs_rp, 0, 0, log_fn);
			return -EFAULT;
		}
	} else {
		args_envs_r = args;
		p->args_len = args_len;
	}
	host_prepare_copy_long_result(args_envs, args_envs_r,
				      p->args_len + sizeof(long) - 1,
				      copy_long_fn);
	if (!args) {
		host_unmap_virtual_result(args_envs_r, args_envs_npages,
					  unmap_virtual_fn);
		host_unmap_memory_result(NULL, args_envs_rp, p->args_len,
					 unmap_memory_fn);
	}
	host_flush_tlb_result(flush_tlb_fn);

	if (!envs) {
		map_size = ((uintptr_t)p->envs & (page_size - 1)) + p->envs_len;
		args_envs_npages = (map_size + page_size - 1) >> page_shift;
		args_envs_rp = host_map_memory_result(
				NULL, (unsigned long)p->envs, p->envs_len,
				map_memory_fn);
		args_envs_r = host_prepare_map_virtual_result(
				args_envs_rp, args_envs_npages, attr,
				map_virtual_fn);
		if (!args_envs_r) {
			if (log_fn)
				host_prepare_args_log_result(
					HOST_PREPARE_ARGS_LOG_ENVS_MAP_FAILED,
					args_envs_rp, 0, 0, log_fn);
			return -EFAULT;
		}
	} else {
		args_envs_r = envs;
		p->envs_len = envs_len;
	}
	envs_offset = (p->args_len + sizeof(long) - 1) & ~(sizeof(long) - 1);
	host_prepare_copy_long_result(args_envs + envs_offset, args_envs_r,
				      p->envs_len + sizeof(long) - 1,
				      copy_long_fn);
	if (!envs) {
		host_unmap_virtual_result(args_envs_r, args_envs_npages,
					  unmap_virtual_fn);
		host_unmap_memory_result(NULL, args_envs_rp, p->envs_len,
					 unmap_memory_fn);
	}
	host_flush_tlb_result(flush_tlb_fn);

	argc = *((long *)args_envs);
	argv = (char **)(args_envs + sizeof(long));
	if (proc->saved_cmdline) {
		host_prepare_free_result(proc->saved_cmdline, free_fn);
		proc->saved_cmdline = NULL;
		proc->saved_cmdline_len = 0;
	}
	proc->saved_cmdline_len =
		p->args_len - ((argc + 2) * sizeof(char **));
	proc->saved_cmdline = host_prepare_alloc_result(
			proc->saved_cmdline_len, alloc_nowait, alloc_fn);
	if (!proc->saved_cmdline) {
		if (log_fn)
			host_prepare_args_log_result(
				HOST_PREPARE_ARGS_LOG_CMDLINE_ALLOC_FAILED,
				proc->saved_cmdline_len, 0, 0, log_fn);
		return -ENOMEM;
	}
	memcpy(proc->saved_cmdline,
	       args_envs + ((argc + 2) * sizeof(char **)),
	       proc->saved_cmdline_len);
	if (log_fn)
		host_prepare_args_log_result(HOST_PREPARE_ARGS_LOG_CMDLINE,
				(unsigned long)proc->saved_cmdline,
				proc->saved_cmdline_len, 0, log_fn);

	for (i = 0; i < argc; i++)
		argv[i] = (char *)addr + (unsigned long)argv[i];

	envc = *((long *)(args_envs + envs_offset));
	env = (char **)(args_envs + envs_offset + sizeof(long));
	for (i = 0; i < envc; i++)
		env[i] = (char *)addr + envs_offset + (unsigned long)env[i];

	if (pn->enable_vdso) {
		if (!arch_map_vdso_fn)
			return -EINVAL;
		error = host_arch_map_vdso_result(vm, arch_map_vdso_fn);
		if (error) {
			if (log_fn)
				host_prepare_args_log_result(
					HOST_PREPARE_ARGS_LOG_VDSO_FAILED,
					error, 0, 0, log_fn);
			return error;
		}
	} else {
		vm->vdso_addr = NULL;
	}

	p->rprocess = (unsigned long)thread;
	p->rpgtable = host_virt_to_phys_result(as->page_table,
					       virt_to_phys_fn);
	error = host_init_process_stack_result(thread, pn, at_base, argc,
					      argv, envc, env, init_stack_fn);
	if (error) {
		if (log_fn)
			host_prepare_args_log_result(
				HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED,
				error, 0, 0, log_fn);
		return error;
	}

	return 0;
}

int host_schedule_process_request_result(struct ikc_scd_packet *request,
					 host_thread_proc_fn_t proc_fn,
					 host_current_cpu_fn_t current_cpu_fn,
					 host_thread_cpu_allowed_fn_t cpu_allowed_fn,
					 host_thread_obtain_cpuid_fn_t obtain_cpuid_fn,
					 host_proc_pid_fn_t proc_pid_fn,
					 host_thread_reg_fn_t pc_fn,
					 host_thread_reg_fn_t sp_fn,
					 host_schedule_invalid_log_fn_t invalid_log_fn,
					 host_schedule_received_log_fn_t received_log_fn,
					 host_schedule_no_cpu_log_fn_t no_cpu_log_fn,
					 host_thread_set_tid_fn_t set_tid_fn,
					 host_status_set_fn_t set_proc_status_fn,
					 host_status_set_fn_t set_thread_status_fn,
					 host_chain_thread_fn_t chain_thread_fn,
					 host_chain_process_fn_t chain_process_fn,
					 host_runq_add_thread_fn_t runq_add_fn,
					 host_schedule_queued_log_fn_t queued_log_fn,
					 int running_status)
{
	void *thread;
	void *proc;
	int cpuid;
	int pid;
	unsigned long pc;
	unsigned long sp;

	if (!request || !proc_fn || !current_cpu_fn || !cpu_allowed_fn ||
	    !obtain_cpuid_fn || !proc_pid_fn || !set_tid_fn ||
	    !set_proc_status_fn || !set_thread_status_fn || !chain_thread_fn ||
	    !chain_process_fn || !runq_add_fn)
		return -EINVAL;

	thread = (void *)request->arg;
	proc = thread ? host_thread_proc_result(thread, proc_fn) : NULL;
	if (!thread || !proc) {
		if (invalid_log_fn)
			host_schedule_invalid_log_result(thread, invalid_log_fn);
		return -EINVAL;
	}

	cpuid = host_current_cpu_result(current_cpu_fn);
	pid = host_proc_pid_result(proc, proc_pid_fn);
	if (received_log_fn) {
		if (!pc_fn || !sp_fn)
			return -EINVAL;
		pc = host_thread_reg_result(thread, pc_fn);
		sp = host_thread_reg_result(thread, sp_fn);
		host_schedule_received_log_result(thread, pid, pc, sp, cpuid,
						  received_log_fn);
	}

	if (!host_thread_cpu_allowed_result(thread, cpuid, cpu_allowed_fn)) {
		cpuid = host_thread_obtain_cpuid_result(thread,
							obtain_cpuid_fn);
		if (cpuid == -1) {
			if (no_cpu_log_fn)
				host_schedule_no_cpu_log_result(no_cpu_log_fn);
			return -1;
		}
	}

	host_thread_set_tid_result(thread, pid, set_tid_fn);
	host_status_set_result(proc, running_status, set_proc_status_fn);
	host_status_set_result(thread, running_status, set_thread_status_fn);
	host_chain_thread_result(thread, chain_thread_fn);
	host_chain_process_result(proc, chain_process_fn);
	host_runq_add_thread_result(thread, cpuid, runq_add_fn);
	if (queued_log_fn)
		host_schedule_queued_log_result(pid, pid, cpuid, running_status,
						queued_log_fn);

	return 0;
}

int host_remote_page_fault_answer_result(void *channel,
					 struct ikc_scd_packet *request,
					 int err,
					 host_ikc_packet_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;

	if (!request || !send_fn)
		return -EINVAL;

	memset(&packet, '\0', sizeof(packet));
	packet.msg = SCD_MSG_REMOTE_PAGE_FAULT_ANSWER;
	packet.ref = request->ref;
	packet.arg = request->arg;
	packet.err = err;
	packet.reply = request->reply;
	packet.pid = request->pid;
	host_ikc_packet_send_result(channel, &packet, send_fn);
	return 0;
}

int host_remote_page_fault_body_result(void *channel,
				       struct ikc_scd_packet *request,
				       int err, void *current_thread,
				       unsigned long populate_flag,
				       int profile_event,
				       host_thread_profile_enabled_fn_t profile_enabled_fn,
				       host_timestamp_fn_t timestamp_fn,
				       host_preempt_fn_t preempt_disable_fn,
				       host_remote_page_fault_fn_t page_fault_fn,
				       host_preempt_fn_t preempt_enable_fn,
				       host_profile_event_fn_t profile_event_fn,
				       host_remote_page_fault_log_fn_t log_fn,
				       host_ikc_packet_send_fn_t send_fn)
{
	unsigned long reason;
	unsigned long start = 0;
	int profile_enabled;

	if (!request || !send_fn)
		return -EINVAL;

	if (err)
		return host_remote_page_fault_answer_result(channel, request,
							   err, send_fn);

	if (!current_thread || !profile_enabled_fn || !preempt_disable_fn ||
	    !page_fault_fn || !preempt_enable_fn)
		return -EINVAL;

	profile_enabled = host_thread_profile_enabled_result(
		current_thread, profile_enabled_fn);
	if (profile_enabled && (!timestamp_fn || !profile_event_fn))
		return -EINVAL;

	if (profile_enabled)
		start = host_timestamp_result(timestamp_fn);

	reason = request->fault_reason | populate_flag;
	if (log_fn)
		host_remote_page_fault_log_result(
			current_thread, request->fault_address, reason, log_fn);

	host_preempt_result(preempt_disable_fn);
	host_remote_page_fault_process_result(
		current_thread, request->fault_address, reason, page_fault_fn);
	host_preempt_result(preempt_enable_fn);

	if (profile_enabled)
		host_profile_event_result(
			profile_event, host_timestamp_result(timestamp_fn) - start,
			profile_event_fn);

	return host_remote_page_fault_answer_result(channel, request, err,
						    send_fn);
}

int host_remote_page_fault_current_result(
		struct ikc_scd_packet *request, int err,
		unsigned long populate_flag, int profile_event,
		host_current_ptr_fn_t response_channel_fn,
		host_current_ptr_fn_t current_thread_fn,
		host_thread_profile_enabled_fn_t profile_enabled_fn,
		host_timestamp_fn_t timestamp_fn,
		host_preempt_fn_t preempt_disable_fn,
		host_remote_page_fault_fn_t page_fault_fn,
		host_preempt_fn_t preempt_enable_fn,
		host_profile_event_fn_t profile_event_fn,
		host_remote_page_fault_log_fn_t log_fn,
		host_ikc_packet_send_fn_t send_fn)
{
	if (!response_channel_fn || !current_thread_fn)
		return -EINVAL;

	return host_remote_page_fault_body_result(
			host_current_ptr_result(response_channel_fn),
			request, err, host_current_ptr_result(current_thread_fn),
			populate_flag, profile_event, profile_enabled_fn,
			timestamp_fn, preempt_disable_fn, page_fault_fn,
			preempt_enable_fn, profile_event_fn, log_fn, send_fn);
}

int host_remote_page_fault_body_dispatch_result(
		struct ikc_scd_packet *request, int err,
		host_remote_page_fault_body_fn_t body_fn)
{
	if (!request || !body_fn)
		return -EINVAL;

	body_fn(request, err);
	return 0;
}

int host_remote_page_fault_request_result(struct ikc_scd_packet *request,
					  host_find_thread_fn_t find_thread_fn,
					  void *current_thread,
					  host_remote_page_fault_body_fn_t body_fn,
					  host_alloc_fn_t alloc_fn,
					  host_packet_copy_fn_t copy_fn,
					  host_remote_page_fault_defer_fn_t defer_fn,
					  host_sched_wakeup_fn_t wakeup_fn,
					  host_thread_unlock_fn_t unlock_fn,
					  host_remote_page_fault_missing_log_fn_t log_fn,
					  host_backlog_fn_t backlog_fn,
					  unsigned long packet_size,
					  unsigned long alloc_flags,
					  int interruptible_state)
{
	void *thread;
	void *deferred_arg;
	int tid;

	if (!request || !find_thread_fn || !body_fn || !unlock_fn)
		return -EINVAL;

	tid = request->fault_tid;
	thread = host_find_thread_result(0, tid, find_thread_fn);
	if (!thread) {
		host_remote_page_fault_missing_log_result(tid, log_fn);
		host_remote_page_fault_body_dispatch_result(request, -EINVAL,
							   body_fn);
		return 0;
	}

	if (thread == current_thread) {
		host_remote_page_fault_body_dispatch_result(request, 0,
							   body_fn);
		host_thread_unlock_result(thread, unlock_fn);
		return 0;
	}

	if (!alloc_fn || !copy_fn || !defer_fn || !wakeup_fn || !backlog_fn)
		return -EINVAL;

	deferred_arg = host_alloc_result(packet_size, alloc_flags, alloc_fn);
	if (!deferred_arg) {
		host_thread_unlock_result(thread, unlock_fn);
		return -ENOMEM;
	}

	host_packet_copy_result(deferred_arg, request, packet_size, copy_fn);
	host_remote_page_fault_defer_result(thread, deferred_arg, backlog_fn,
					    defer_fn);
	host_sched_wakeup_result(thread, interruptible_state, wakeup_fn);
	host_thread_unlock_result(thread, unlock_fn);
	return 0;
}

int host_traditional_reply_result(void *channel,
				  struct ikc_scd_packet *request,
				  int msg, int err,
				  host_ikc_packet_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;

	if (!request || !send_fn)
		return -EINVAL;

	memset(&packet, '\0', sizeof(packet));
	packet.msg = msg;
	packet.err = err;
	packet.ref = request->ref;
	packet.arg = request->arg;
	packet.reply = request->reply;
	host_ikc_packet_send_result(channel, &packet, send_fn);
	return 0;
}

int host_arg_reply_result(void *channel,
			  struct ikc_scd_packet *request,
			  int msg, int err,
			  host_ikc_packet_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;

	if (!request || !send_fn)
		return -EINVAL;

	memset(&packet, '\0', sizeof(packet));
	packet.msg = msg;
	packet.err = err;
	packet.arg = request->arg;
	packet.reply = request->reply;
	host_ikc_packet_send_result(channel, &packet, send_fn);
	return 0;
}

int host_reply_only_result(void *channel,
			   struct ikc_scd_packet *request,
			   int msg, int err,
			   host_ikc_packet_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;

	if (!request || !send_fn)
		return -EINVAL;

	memset(&packet, '\0', sizeof(packet));
	packet.msg = msg;
	packet.err = err;
	packet.reply = request->reply;
	host_ikc_packet_send_result(channel, &packet, send_fn);
	return 0;
}

int host_perf_ctrl_result(struct perf_ctrl_desc *desc,
			  host_perf_init_raw_fn_t init_raw_fn,
			  host_perf_stop_fn_t stop_fn,
			  host_perf_reset_fn_t reset_fn,
			  host_perf_start_fn_t start_fn,
			  host_perf_read_fn_t read_fn,
			  host_perf_unexpected_fn_t unexpected_fn)
{
	unsigned int mode = 0;
	int ret = 0;

	if (!desc)
		return -EINVAL;

	switch (desc->ctrl_type) {
	case PERF_CTRL_SET:
		if (!init_raw_fn || !stop_fn || !reset_fn)
			return -EINVAL;
		if (!desc->exclude_kernel)
			mode |= PERFCTR_KERNEL_MODE;
		if (!desc->exclude_user)
			mode |= PERFCTR_USER_MODE;

		ret = host_perf_init_raw_result(desc->target_cntr,
						desc->config, mode,
						init_raw_fn);
		if (ret != 0)
			break;

		ret = host_perf_stop_result(1 << desc->target_cntr, 0,
					    stop_fn);
		if (ret != 0)
			break;

		ret = host_perf_reset_result(desc->target_cntr, reset_fn);
		break;

	case PERF_CTRL_ENABLE:
		if (!start_fn)
			return -EINVAL;
		ret = host_perf_start_result(desc->target_cntr_mask, start_fn);
		break;

	case PERF_CTRL_DISABLE:
		if (!stop_fn)
			return -EINVAL;
		ret = host_perf_stop_result(desc->target_cntr_mask,
				IHK_MC_PERFCTR_DISABLE_INTERRUPT, stop_fn);
		break;

	case PERF_CTRL_GET:
		if (!read_fn)
			return -EINVAL;
		desc->read_value = host_perf_read_result(desc->target_cntr,
							 read_fn);
		break;

	default:
		if (unexpected_fn)
			host_perf_unexpected_result(unexpected_fn);
		break;
	}

	return ret;
}

int host_perf_ctrl_request_result(void *channel,
				  struct ikc_scd_packet *request,
				  host_map_memory_fn_t map_memory_fn,
				  host_map_virtual_fn_t map_virtual_fn,
				  host_unmap_virtual_fn_t unmap_virtual_fn,
				  host_unmap_memory_fn_t unmap_memory_fn,
				  host_perf_init_raw_fn_t init_raw_fn,
				  host_perf_stop_fn_t stop_fn,
				  host_perf_reset_fn_t reset_fn,
				  host_perf_start_fn_t start_fn,
				  host_perf_read_fn_t read_fn,
				  host_perf_unexpected_fn_t unexpected_fn,
				  host_ikc_packet_send_fn_t send_fn)
{
	struct perf_ctrl_desc *desc;
	unsigned long phys;
	int ret;

	if (!request || !map_memory_fn || !map_virtual_fn ||
	    !unmap_virtual_fn || !unmap_memory_fn || !send_fn)
		return -EINVAL;

	phys = host_map_memory_result(NULL, request->arg, sizeof(*desc),
				      map_memory_fn);
	desc = host_map_virtual_result(phys, 1,
				       PTATTR_WRITABLE | PTATTR_ACTIVE,
				       map_virtual_fn);

	ret = host_perf_ctrl_result(desc, init_raw_fn, stop_fn, reset_fn,
				    start_fn, read_fn, unexpected_fn);

	if (desc)
		host_unmap_virtual_result(desc, 1, unmap_virtual_fn);
	host_unmap_memory_result(NULL, phys, sizeof(*desc), unmap_memory_fn);

	host_arg_reply_result(channel, request, SCD_MSG_PERF_ACK, ret, send_fn);
	return ret;
}

int host_cpu_rw_reg_request_result(void *channel,
				   struct ikc_scd_packet *request,
				   host_map_memory_fn_t map_memory_fn,
				   host_map_virtual_fn_t map_virtual_fn,
				   host_unmap_virtual_fn_t unmap_virtual_fn,
				   host_unmap_memory_fn_t unmap_memory_fn,
				   host_cpu_rw_register_fn_t rw_register_fn,
				   host_ikc_packet_send_fn_t send_fn)
{
	void *desc;
	unsigned long phys;
	int ret;

	if (!request || !map_memory_fn || !map_virtual_fn ||
	    !unmap_virtual_fn || !unmap_memory_fn || !rw_register_fn ||
	    !send_fn)
		return -EINVAL;

	phys = host_map_memory_result(NULL, request->pdesc,
			sizeof(struct ihk_os_cpu_register), map_memory_fn);
	desc = host_map_virtual_result(phys, 1,
			PTATTR_WRITABLE | PTATTR_ACTIVE, map_virtual_fn);
	ret = desc ? host_cpu_rw_register_result(desc, request->op,
						 rw_register_fn) : -EINVAL;

	if (desc)
		host_unmap_virtual_result(desc, 1, unmap_virtual_fn);
	host_unmap_memory_result(NULL, phys, sizeof(struct ihk_os_cpu_register),
				 unmap_memory_fn);

	host_reply_only_result(channel, request, SCD_MSG_CPU_RW_REG_RESP, ret,
			       send_fn);
	return ret;
}

int host_cleanup_process_request_result(void *channel,
					struct ikc_scd_packet *request,
					host_cleanup_process_fn_t cleanup_fn,
					host_terminate_host_fn_t terminate_fn,
					host_cleanup_process_log_fn_t log_fn,
					host_ikc_packet_send_fn_t send_fn)
{
	int ret;

	if (!request || !cleanup_fn || !terminate_fn || !send_fn)
		return -EINVAL;

	if (log_fn)
		host_cleanup_process_log_result(request->pid, request->arg,
						log_fn);
	ret = host_cleanup_process_result(request->pid, cleanup_fn);
	host_traditional_reply_result(channel, request,
				      SCD_MSG_CLEANUP_PROCESS_RESP, ret,
				      send_fn);
	host_terminate_host_result(request->pid, (void *)request->arg,
				   terminate_fn);
	return 0;
}

int host_cleanup_fd_request_result(void *channel,
				   struct ikc_scd_packet *request,
				   host_cleanup_fd_fn_t cleanup_fn,
				   host_cleanup_fd_log_fn_t log_fn,
				   host_ikc_packet_send_fn_t send_fn)
{
	int ret;

	if (!request || !cleanup_fn || !send_fn)
		return -EINVAL;

	ret = host_cleanup_fd_result(request->pid, (int)request->arg,
				     cleanup_fn);
	if (log_fn)
		host_cleanup_fd_log_result(request->pid, request->arg, ret,
					   log_fn);
	host_traditional_reply_result(channel, request,
				      SCD_MSG_CLEANUP_FD_RESP, ret,
				      send_fn);
	return 0;
}

int host_send_signal_request_result(void *channel,
				    struct ikc_scd_packet *request,
				    host_map_memory_fn_t map_memory_fn,
				    host_map_virtual_fn_t map_virtual_fn,
				    host_unmap_virtual_fn_t unmap_virtual_fn,
				    host_unmap_memory_fn_t unmap_memory_fn,
				    host_do_kill_fn_t do_kill_fn,
				    host_send_signal_log_fn_t log_fn,
				    host_ikc_packet_send_fn_t send_fn)
{
	struct host_mcctrl_signal *mapped;
	struct host_mcctrl_signal info;
	unsigned long phys;
	int rc;

	if (!request || !map_memory_fn || !map_virtual_fn ||
	    !unmap_virtual_fn || !unmap_memory_fn || !do_kill_fn || !send_fn)
		return -EINVAL;

	phys = host_map_memory_result(NULL, request->arg, sizeof(info),
				      map_memory_fn);
	mapped = host_map_virtual_result(phys, 1,
					 PTATTR_WRITABLE | PTATTR_ACTIVE,
					 map_virtual_fn);
	if (!mapped) {
		host_unmap_memory_result(NULL, phys, sizeof(info),
					 unmap_memory_fn);
		host_traditional_reply_result(channel, request,
					      SCD_MSG_SEND_SIGNAL_ACK,
					      -EINVAL, send_fn);
		return -EINVAL;
	}

	memcpy(&info, mapped, sizeof(info));
	host_unmap_virtual_result(mapped, 1, unmap_virtual_fn);
	host_unmap_memory_result(NULL, phys, sizeof(info), unmap_memory_fn);

	host_traditional_reply_result(channel, request, SCD_MSG_SEND_SIGNAL_ACK,
				      0, send_fn);
	rc = (int)host_do_kill_result(info.pid, info.tid, info.sig,
				      info.info, do_kill_fn);
	if (log_fn)
		host_send_signal_log_result(info.pid, info.tid, info.sig, rc,
					    log_fn);
	return 0;
}

int host_wake_syscall_thread_request_result(struct ikc_scd_packet *request,
					    host_find_thread_fn_t find_thread_fn,
					    host_wakeup_thread_fn_t wakeup_fn,
					    host_thread_unlock_fn_t unlock_fn,
					    host_wake_syscall_log_fn_t log_fn)
{
	void *thread;
	int tid;

	if (!request || !find_thread_fn || !wakeup_fn || !unlock_fn)
		return -EINVAL;

	tid = request->ttid;
	thread = host_find_thread_result(0, tid, find_thread_fn);
	if (!thread) {
		if (log_fn)
			host_wake_syscall_log_result(tid, 0, log_fn);
		return -EINVAL;
	}

	if (log_fn)
		host_wake_syscall_log_result(tid, 1, log_fn);
	host_wakeup_thread_result(thread, wakeup_fn);
	host_thread_unlock_result(thread, unlock_fn);
	return 0;
}

int host_debug_log_request_result(struct ikc_scd_packet *request,
				  host_debug_log_fn_t debug_fn,
				  host_debug_log_print_fn_t print_fn)
{
	unsigned long code;

	if (!request || !debug_fn)
		return -EINVAL;

	code = request->arg;
	if (print_fn)
		host_debug_log_print_result(code, print_fn);
	return host_debug_log_result(code, debug_fn);
}

int host_response_packet_result(void *response_channel,
				struct ikc_scd_packet *packet,
				host_response_packet_fn_t response_fn)
{
	if (!packet || !response_fn)
		return -EINVAL;

	return response_fn(response_channel, packet);
}

int host_packet_dispatch_result(struct ikc_scd_packet *packet,
				host_packet_dispatch_fn_t dispatch_fn)
{
	if (!packet || !dispatch_fn)
		return -EINVAL;

	return dispatch_fn(packet);
}

int host_remote_page_fault_dispatch_result(
		struct ikc_scd_packet *packet, void *current_thread,
		host_remote_page_fault_dispatch_fn_t dispatch_fn)
{
	if (!packet || !dispatch_fn)
		return -EINVAL;

	return dispatch_fn(packet, current_thread);
}

int host_procfs_packet_dispatch_result(struct ikc_scd_packet *packet,
				       host_procfs_request_fn_t request_fn)
{
	if (!packet || !request_fn)
		return -EINVAL;

	request_fn(packet);
	return 0;
}

int host_scd_packet_dispatch_result(void *channel,
				    struct ikc_scd_packet *packet,
				    void *response_channel,
				    void *current_thread,
				    const struct host_scd_dispatch_ops *ops,
				    unsigned long populate_flag,
				    int profile_event,
				    unsigned long packet_size,
				    unsigned long alloc_flags,
				    int interruptible_state,
				    int running_status)
{
	int ret = 0;

	if (!packet || !ops || !ops->release_packet_fn)
		return -EINVAL;

	switch (packet->msg) {
	case SCD_MSG_INIT_CHANNEL_ACKED:
		if (ops->init_ack_log_fn)
			host_init_ack_log_result(ops->init_ack_log_fn);
		ret = 0;
		break;
	case SCD_MSG_PREPARE_PROCESS:
		if (ops->prepare_process_fn) {
			host_response_packet_result(response_channel, packet,
						    ops->prepare_process_fn);
			ret = 0;
		}
		else {
			ret = -EINVAL;
		}
		break;
	case SCD_MSG_SCHEDULE_PROCESS:
		ret = host_packet_dispatch_result(packet,
						  ops->schedule_process_fn);
		break;
	case SCD_MSG_WAKE_UP_SYSCALL_THREAD:
		ret = host_packet_dispatch_result(packet,
						  ops->wake_syscall_thread_fn);
		break;
	case SCD_MSG_REMOTE_PAGE_FAULT:
		ret = host_remote_page_fault_dispatch_result(
				packet, current_thread, ops->remote_page_fault_fn);
		break;
	case SCD_MSG_SEND_SIGNAL:
		if (ops->send_signal_fn) {
			host_response_packet_result(response_channel, packet,
						    ops->send_signal_fn);
			ret = 0;
		}
		else {
			ret = -EINVAL;
		}
		break;
	case SCD_MSG_PROCFS_REQUEST:
	case SCD_MSG_PROCFS_RELEASE:
		ret = host_procfs_packet_dispatch_result(
				packet, ops->procfs_request_fn);
		break;
	case SCD_MSG_CLEANUP_PROCESS:
		if (ops->cleanup_process_fn) {
			host_response_packet_result(response_channel, packet,
						    ops->cleanup_process_fn);
			ret = 0;
		}
		else {
			ret = -EINVAL;
		}
		break;
	case SCD_MSG_CLEANUP_FD:
		if (ops->cleanup_fd_fn) {
			host_response_packet_result(response_channel, packet,
						    ops->cleanup_fd_fn);
			ret = 0;
		}
		else {
			ret = -EINVAL;
		}
		break;
	case SCD_MSG_DEBUG_LOG:
		ret = host_packet_dispatch_result(packet, ops->debug_log_fn);
		break;
	case SCD_MSG_SYSFS_REQ_SHOW:
	case SCD_MSG_SYSFS_REQ_STORE:
	case SCD_MSG_SYSFS_REQ_RELEASE:
		ret = host_sysfs_packet_result(channel, packet->msg,
					       packet->err,
					       packet->sysfs_arg1,
					       packet->sysfs_arg2,
					       packet->sysfs_arg3,
					       ops->sysfs_packet_fn);
		break;
	case SCD_MSG_PERF_CTRL:
		ret = host_response_packet_result(response_channel, packet,
						  ops->perf_ctrl_fn);
		break;
	case SCD_MSG_CPU_RW_REG:
		if (ops->cpu_rw_reg_fn) {
			host_response_packet_result(response_channel, packet,
						    ops->cpu_rw_reg_fn);
			ret = 0;
		}
		else {
			ret = -EINVAL;
		}
		break;
	default:
		if (ops->unknown_packet_log_fn)
			host_unknown_packet_log_result(
					packet, ops->unknown_packet_log_fn);
		ret = 0;
		break;
	}

	host_release_packet_result(packet, ops->release_packet_fn);
	(void)populate_flag;
	(void)profile_event;
	(void)packet_size;
	(void)alloc_flags;
	(void)interruptible_state;
	(void)running_status;
	return ret;
}

int host_prepare_process_request_result(
		void *channel, struct ikc_scd_packet *request,
		host_prepare_process_fn_t prepare_fn,
		host_ikc_packet_send_fn_t send_fn)
{
	int ret;

	if (!request || !prepare_fn)
		return -EINVAL;

	ret = host_prepare_process_result(request->arg, prepare_fn);
	return host_traditional_reply_result(channel, request,
			SCD_MSG_PREPARE_PROCESS_ACKED, ret, send_fn);
}

int host_procfs_request_result(struct ikc_scd_packet *request,
			       host_procfs_request_fn_t procfs_request_fn)
{
	if (!request || !procfs_request_fn)
		return -EINVAL;

	return procfs_request_fn(request);
}

int host_sysfs_packet_result(void *channel, int msg, int err,
			     long arg1, long arg2, long arg3,
			     host_sysfs_packet_fn_t sysfs_packet_fn)
{
	if (!sysfs_packet_fn)
		return -EINVAL;

	sysfs_packet_fn(channel, msg, err, arg1, arg2, arg3);
	return 0;
}

int host_unknown_packet_log_result(struct ikc_scd_packet *packet,
				   host_unknown_packet_log_fn_t log_fn)
{
	if (!packet || !log_fn)
		return -EINVAL;

	log_fn(packet);
	return 0;
}

int host_release_packet_result(struct ikc_scd_packet *packet,
			       host_release_packet_fn_t release_packet_fn)
{
	if (!packet || !release_packet_fn)
		return -EINVAL;

	release_packet_fn(packet);
	return 0;
}

int host_release_packet_dispatch_result(
		struct ikc_scd_packet *packet,
		host_release_packet_fn_t release_packet_fn)
{
	if (!release_packet_fn)
		return -EINVAL;

	release_packet_fn(packet);
	return 0;
}

int host_procfs_answer_current_result(
		struct ikc_scd_packet *request, int err,
		host_current_ptr_fn_t response_channel_fn,
		host_ikc_packet_send_fn_t send_fn)
{
	if (!response_channel_fn)
		return -EINVAL;

	return procfs_answer_result(host_current_ptr_result(response_channel_fn),
				    request, err, send_fn);
}

int host_syscall_packet_handler_result(void *channel, void *packet, void *os,
				       const struct host_scd_dispatch_ops *ops,
				       host_current_ptr_fn_t response_channel_fn,
				       host_current_ptr_fn_t current_thread_fn,
				       unsigned long populate_flag,
				       int profile_event,
				       unsigned long packet_size,
				       unsigned long alloc_flags,
				       int interruptible_state,
				       int running_status)
{
	(void)os;
	if (!response_channel_fn || !current_thread_fn)
		return -EINVAL;

	return host_scd_packet_dispatch_result(channel, packet,
			host_current_ptr_result(response_channel_fn),
			host_current_ptr_result(current_thread_fn), ops,
			populate_flag, profile_event, packet_size,
			alloc_flags, interruptible_state, running_status);
}

int host_dummy_packet_handler_result(void *channel, void *packet, void *os,
				     host_release_packet_fn_t release_packet_fn)
{
	(void)channel;
	(void)os;
	return host_release_packet_dispatch_result(packet, release_packet_fn);
}

int host_init_ikc2linux_result(int linux_cpu,
			       struct ihk_ikc_channel_desc ***ikc2linuxsp,
			       int nr_linux_cores, int num_processors,
			       unsigned long packet_size,
			       unsigned long page_size,
			       unsigned long alloc_flags,
			       host_alloc_fn_t alloc_fn,
			       host_ikc_connect_fn_t connect_fn,
			       host_delay_fn_t delay_fn,
			       host_set_current_ikc2linux_fn_t set_current_fn,
			       host_ikc_packet_handler_fn_t dummy_handler_fn,
			       host_init_ikc_log_fn_t log_fn,
			       host_panic_fn_t panic_fn)
{
	struct ihk_ikc_channel_desc **channels;
	struct ihk_ikc_connect_param param;
	struct ihk_ikc_channel_desc *channel;
	unsigned long table_bytes;
	unsigned long queue_size;

	if (!ikc2linuxsp || !alloc_fn || !connect_fn || !delay_fn ||
	    !set_current_fn || !dummy_handler_fn)
		return -EINVAL;

	if (!*ikc2linuxsp) {
		table_bytes = sizeof(**ikc2linuxsp) * (unsigned long)nr_linux_cores;
		channels = host_alloc_result(table_bytes, alloc_flags, alloc_fn);
		if (!channels) {
			host_init_ikc_log_result(HOST_INIT_IKC_LOG_ALLOC_ERROR,
						 log_fn);
			host_panic_result(panic_fn);
			return -ENOMEM;
		}
		memset(channels, 0, table_bytes);
		*ikc2linuxsp = channels;
	}

	channels = *ikc2linuxsp;
	channel = channels[linux_cpu];
	if (!channel) {
		memset(&param, 0, sizeof(param));
		param.port = 503;
		param.intr_cpu = linux_cpu;
		param.pkt_size = (int)packet_size;
		queue_size = 4UL * (unsigned long)num_processors * packet_size;
		if (queue_size < page_size * 4UL)
			queue_size = page_size * 4UL;
		param.queue_size = (int)queue_size;
		param.magic = 0x1129;
		param.handler = dummy_handler_fn;

		host_init_ikc_log_result(HOST_INIT_IKC_LOG_TRY_CONNECT,
					 log_fn);
		while (host_ikc_connect_result(&param, connect_fn) != 0) {
			host_init_ikc_log_result(HOST_INIT_IKC_LOG_RETRY_DOT,
						 log_fn);
			host_delay_result(1000UL * 1000UL, delay_fn);
		}
		host_init_ikc_log_result(HOST_INIT_IKC_LOG_CONNECTED, log_fn);

		channel = param.channel;
		channels[linux_cpu] = channel;
	}

	return host_set_current_ikc2linux_result(channel, set_current_fn);
}

int host_init_ikc2mckernel_result(unsigned long packet_size,
				  unsigned long page_size, int processor_id,
				  host_ikc_packet_handler_fn_t handler_fn,
				  host_ikc_connect_fn_t connect_fn,
				  host_delay_fn_t delay_fn,
				  host_ikc_set_regular_channel_fn_t set_regular_fn,
				  host_init_ikc_log_fn_t log_fn)
{
	struct ihk_ikc_connect_param param;

	if (!handler_fn || !connect_fn || !delay_fn || !set_regular_fn)
		return -EINVAL;

	memset(&param, 0, sizeof(param));
	param.port = 501;
	param.intr_cpu = -1;
	param.pkt_size = (int)packet_size;
	param.queue_size = (int)(page_size * 4UL);
	param.magic = 0x1329;
	param.handler = handler_fn;

	host_init_ikc_log_result(HOST_INIT_IKC_LOG_TRY_CONNECT, log_fn);
	while (host_ikc_connect_result(&param, connect_fn) != 0) {
		host_init_ikc_log_result(HOST_INIT_IKC_LOG_RETRY_DOT, log_fn);
		host_delay_result(1000UL * 1000UL, delay_fn);
	}
	host_init_ikc_log_result(HOST_INIT_IKC_LOG_CONNECTED, log_fn);

	return host_ikc_set_regular_channel_result(param.channel, processor_id,
						   set_regular_fn);
}

int host_init_ikc2linux_public_result(
		int linux_cpu, struct ihk_ikc_channel_desc ***ikc2linuxsp,
		int nr_linux_cores, int num_processors,
		unsigned long packet_size, unsigned long page_size,
		unsigned long alloc_flags, host_alloc_fn_t alloc_fn,
		host_ikc_connect_fn_t connect_fn, host_delay_fn_t delay_fn,
		host_set_current_ikc2linux_fn_t set_current_fn,
		host_ikc_packet_handler_fn_t dummy_handler_fn,
		host_init_ikc_log_fn_t log_fn, host_panic_fn_t panic_fn)
{
	int rc;

	rc = host_init_ikc2linux_result(linux_cpu, ikc2linuxsp,
			nr_linux_cores, num_processors, packet_size, page_size,
			alloc_flags, alloc_fn, connect_fn, delay_fn,
			set_current_fn, dummy_handler_fn, log_fn, panic_fn);
	if (rc)
		host_panic_result(panic_fn);
	return rc;
}

int host_init_ikc2mckernel_public_result(
		unsigned long packet_size, unsigned long page_size,
		int processor_id, host_ikc_packet_handler_fn_t handler_fn,
		host_ikc_connect_fn_t connect_fn, host_delay_fn_t delay_fn,
		host_ikc_set_regular_channel_fn_t set_regular_fn,
		host_init_ikc_log_fn_t log_fn, host_panic_fn_t panic_fn)
{
	int rc;

	rc = host_init_ikc2mckernel_result(packet_size, page_size,
			processor_id, handler_fn, connect_fn, delay_fn,
			set_regular_fn, log_fn);
	if (rc)
		host_panic_result(panic_fn);
	return rc;
}

#endif
