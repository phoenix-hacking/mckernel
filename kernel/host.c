/* host.c COPYRIGHT FUJITSU LIMITED 2015-2018 */
/**
 * \file host.c
 *  License details are found in the file LICENSE.
 * \brief
 *  host call handlers
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * 	Copyright (C) 2012  RIKEN AICS
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <ihk/mm.h>
#include <ihk/ikc.h>
#include <ikc/master.h>
#include <cls.h>
#include <syscall.h>
#include <process.h>
#include <page.h>
#include <mman.h>
#include <init.h>
#include <host_helpers.h>
#include <kmalloc.h>
#include <object_helpers.h>
#include <sysfs.h>
#include <ihk/perfctr.h>
#include <rusage_private.h>
#include <ihk/debug.h>

//#define DEBUG_PRINT_HOST

#ifdef DEBUG_PRINT_HOST
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

/* Linux channel table, indexec by Linux CPU id */
struct ihk_ikc_channel_desc **ikc2linuxs;

void check_mapping_for_proc(struct thread *thread, unsigned long addr)
{
	unsigned long __phys;

	if (ihk_mc_pt_virt_to_phys(thread->vm->address_space->page_table, (void*)addr, &__phys)) {
		kprintf("check_map: no mapping for 0x%lX\n", addr);
	}
	else {
		kprintf("check_map: 0x%lX -> 0x%lX\n", addr, __phys);
	}
}

static int host_prepare_add_range_raw_bridge(void *vm, unsigned long start,
					     unsigned long end,
					     unsigned long phys,
					     unsigned long flag,
					     int pgshift, void **rangep)
{
	struct vm_range *range = NULL;
	int rc;

	rc = add_process_memory_range((struct process_vm *)vm, start, end, phys,
			flag, NULL, 0, pgshift, NULL, &range);
	if (rangep)
		*rangep = range;
	return rc;
}

static int host_prepare_add_range_bridge(void *vm, unsigned long start,
					 unsigned long end,
					 unsigned long phys,
					 unsigned long flag,
					 int pgshift, void **rangep)
{
	return host_prepare_add_range_result(vm, start, end, phys, flag,
			pgshift, rangep, host_prepare_add_range_raw_bridge);
}

static void *host_prepare_alloc_pages_user_raw_bridge(int npages,
						      unsigned long flags,
						      unsigned long virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
}

static void *host_prepare_alloc_pages_user_bridge(int npages,
						  unsigned long flags,
						  unsigned long virt_addr)
{
	return host_prepare_alloc_pages_user_result(npages, flags, virt_addr,
			host_prepare_alloc_pages_user_raw_bridge);
}

static void host_prepare_free_pages_user_raw_bridge(void *addr, int npages)
{
	_ihk_mc_free_pages(addr, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
}

static void host_prepare_free_pages_user_bridge(void *addr, int npages)
{
	host_prepare_free_pages_user_result(addr, npages,
			host_prepare_free_pages_user_raw_bridge);
}

static unsigned long host_prepare_virt_to_phys_raw_bridge(void *addr)
{
	return virt_to_phys(addr);
}

static unsigned long host_prepare_virt_to_phys_bridge(void *addr)
{
	return host_virt_to_phys_result(addr,
			host_prepare_virt_to_phys_raw_bridge);
}

static unsigned long host_prepare_arch_vrflag_to_ptattr_raw_bridge(
		unsigned long flag, unsigned long fault, void *ptep)
{
	return arch_vrflag_to_ptattr(flag, fault, ptep);
}

static unsigned long host_prepare_arch_vrflag_to_ptattr_bridge(
		unsigned long flag, unsigned long fault, void *ptep)
{
	return host_arch_vrflag_to_ptattr_result(flag, fault, ptep,
			host_prepare_arch_vrflag_to_ptattr_raw_bridge);
}

static int host_prepare_pt_set_range_raw_bridge(void *page_table, void *vm,
						unsigned long start,
						unsigned long end,
						unsigned long phys,
						unsigned long attr,
						int pgshift, void *range,
						int flags)
{
	return ihk_mc_pt_set_range(page_table, vm, (void *)start, (void *)end,
			phys, attr, pgshift, range, flags);
}

static int host_prepare_pt_set_range_bridge(void *page_table, void *vm,
					    unsigned long start,
					    unsigned long end,
					    unsigned long phys,
					    unsigned long attr,
					    int pgshift, void *range,
					    int flags)
{
	return host_pt_set_range_result(page_table, vm, start, end, phys,
			attr, pgshift, range, flags,
			host_prepare_pt_set_range_raw_bridge);
}

static void host_prepare_modify_user_context_raw_bridge(void *uctx, int reg,
							unsigned long value)
{
	ihk_mc_modify_user_context(uctx, reg, value);
}

static void host_prepare_modify_user_context_bridge(void *uctx, int reg,
						    unsigned long value)
{
	host_modify_user_context_result(uctx, reg, value,
			host_prepare_modify_user_context_raw_bridge);
}

static void host_prepare_ranges_log_raw_bridge(int event, unsigned long arg0,
					       unsigned long arg1,
					       unsigned long arg2)
{
	switch (event) {
	case HOST_PREPARE_RANGES_LOG_AP_USER:
		dkprintf("%s: section: %lu size: %lu pages -> IHK_MC_AP_USER\n",
				__FUNCTION__, arg0, arg1);
		break;
	case HOST_PREPARE_RANGES_LOG_ADD_FAILED:
		kprintf("ERROR: adding memory range for ELF section %lu\n",
				arg0);
		break;
	case HOST_PREPARE_RANGES_LOG_ALLOC_FAILED:
		kprintf("ERROR: alloc pages for ELF section %lu\n", arg0);
		break;
	case HOST_PREPARE_RANGES_LOG_PT_FAILED:
		kprintf("%s: ihk_mc_pt_set_range failed. %lu\n",
				__FUNCTION__, arg1);
		break;
	case HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE:
		kprintf("%s: ERROR: data section is too large (end addr: %lx)\n",
				__FUNCTION__, arg0);
		break;
	default:
		(void)arg2;
		break;
	}
}

static void host_prepare_ranges_log_bridge(int event, unsigned long arg0,
					   unsigned long arg1,
					   unsigned long arg2)
{
	host_prepare_ranges_log_result(event, arg0, arg1, arg2,
			host_prepare_ranges_log_raw_bridge);
}

static int host_prepare_arch_map_vdso_raw_bridge(void *vm)
{
	return arch_map_vdso((struct process_vm *)vm);
}

static int host_prepare_arch_map_vdso_bridge(void *vm)
{
	return host_arch_map_vdso_result(vm,
			host_prepare_arch_map_vdso_raw_bridge);
}

static int host_prepare_init_stack_raw_bridge(void *thread,
					      struct program_load_desc *pn,
					      unsigned long at_base, int argc,
					      char **argv, int envc, char **env)
{
	return init_process_stack((struct thread *)thread, pn, at_base, argc,
			argv, envc, env);
}

static int host_prepare_init_stack_bridge(void *thread,
					  struct program_load_desc *pn,
					  unsigned long at_base, int argc,
					  char **argv, int envc, char **env)
{
	return host_init_process_stack_result(thread, pn, at_base, argc, argv,
			envc, env, host_prepare_init_stack_raw_bridge);
}

static void host_prepare_args_log_raw_bridge(int event, unsigned long arg0,
					     unsigned long arg1,
					     unsigned long arg2)
{
	switch (event) {
	case HOST_PREPARE_ARGS_LOG_ALLOC_FAILED:
		kprintf("ERROR: allocating pages for args/envs\n");
		break;
	case HOST_PREPARE_ARGS_LOG_ADD_FAILED:
		kprintf("ERROR: adding memory range for args/envs\n");
		break;
	case HOST_PREPARE_ARGS_LOG_ARGS_MAP_FAILED:
	case HOST_PREPARE_ARGS_LOG_ENVS_MAP_FAILED:
		(void)arg0;
		break;
	case HOST_PREPARE_ARGS_LOG_CMDLINE_ALLOC_FAILED:
		(void)arg0;
		break;
	case HOST_PREPARE_ARGS_LOG_VDSO_FAILED:
		kprintf("ERROR: mapping vdso pages. %lu\n", arg0);
		break;
	case HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED:
		kprintf("%s: error: init_process_stack failed with %lu\n",
			__func__, arg0);
		break;
	case HOST_PREPARE_ARGS_LOG_CMDLINE:
		dkprintf("%s: saved_cmdline: %s\n", __FUNCTION__,
			(char *)arg0);
		break;
	default:
		(void)arg1;
		(void)arg2;
		break;
	}
}

static void host_prepare_args_log_bridge(int event, unsigned long arg0,
					 unsigned long arg1,
					 unsigned long arg2)
{
	host_prepare_args_log_result(event, arg0, arg1, arg2,
			host_prepare_args_log_raw_bridge);
}

static unsigned long host_map_memory_bridge(void *os, unsigned long phys,
					    unsigned long size);
static void *host_prepare_map_virtual_bridge(unsigned long phys, int npages,
					     unsigned long attr);
static void host_unmap_virtual_bridge(void *addr, int npages);
static void host_unmap_memory_bridge(void *os, unsigned long phys,
				     unsigned long size);
static void host_prepare_free_bridge(void *ptr);
static void *host_prepare_alloc_bridge(unsigned long size, unsigned long flags);
static void host_prepare_copy_long_bridge(void *dst, const void *src,
					  unsigned long size);
static void host_prepare_flush_tlb_bridge(void);

/* 
 * Prepares the process ranges based on the ELF header described 
 * in program_load_desc and updates physical address in "p" so that
 * host can copy program image.
 * It also prepares args, envs and the process stack.
 * 
 * NOTE: if args, args_len, envs, envs_len are zero, 
 * the function constructs them based on the descriptor 
 */
int prepare_process_ranges_args_envs(struct thread *thread, 
		struct program_load_desc *pn,
		struct program_load_desc *p,
		enum ihk_mc_pt_attribute attr,
		char *args, int args_len,
		char *envs, int envs_len) 
{
	struct process *proc = thread->proc;
	unsigned long at_base = 0;
	int error;
	int n;
	
	n = p->num_sections;
	error = host_prepare_ranges_sections_result(thread, pn, p, &at_base,
			PAGE_SIZE, PAGE_MASK, LARGE_PAGE_SIZE, LARGE_PAGE_MASK,
			TASK_UNMAPPED_BASE, PAGE_SHIFT, LARGE_PAGE_SHIFT,
			IHK_MC_AP_NOWAIT, IHK_MC_AP_USER, MPOL_NO_BSS,
			PF_POPULATE, IHK_UCR_PROGRAM_COUNTER,
			host_prepare_add_range_bridge,
			host_prepare_alloc_pages_user_bridge,
			host_prepare_free_pages_user_bridge,
			host_prepare_virt_to_phys_bridge,
			host_prepare_arch_vrflag_to_ptattr_bridge,
			host_prepare_pt_set_range_bridge,
			host_prepare_modify_user_context_bridge,
			host_prepare_ranges_log_bridge);
	if (error)
		goto err;

	error = host_prepare_ranges_args_envs_result(thread, pn, p, attr,
			args, args_len, envs, envs_len, at_base, PAGE_SIZE,
			PAGE_MASK, PAGE_SHIFT, IHK_MC_AP_NOWAIT,
			host_prepare_add_range_bridge,
			host_prepare_alloc_pages_user_bridge,
			host_prepare_free_pages_user_bridge,
			host_prepare_virt_to_phys_bridge,
			host_map_memory_bridge,
			host_prepare_map_virtual_bridge,
			host_unmap_virtual_bridge,
			host_unmap_memory_bridge,
			host_prepare_copy_long_bridge,
			host_prepare_alloc_bridge,
			host_prepare_free_bridge,
			host_prepare_flush_tlb_bridge,
			host_prepare_arch_map_vdso_bridge,
			host_prepare_init_stack_bridge,
			host_prepare_args_log_bridge);
	if (error)
		goto err;

	kprintf("mcexec_v10: prepared pid=%d thread=%p entry=0x%lx sp=0x%lx sections=%d\n",
		proc->pid, thread, p->entry,
		thread->uctx ? ihk_mc_syscall_sp(thread->uctx) : 0UL, n);

	return 0;

err:
	/* TODO: cleanup allocated ranges */
	return error;
}

/*
 * Communication with host
 */
static int host_prepare_monitor_status_raw_bridge(int cpu)
{
	struct cpu_local_var *clv = get_cpu_local_var(cpu);

	return clv->monitor->status;
}

static int host_prepare_monitor_status_bridge(int cpu)
{
	return host_monitor_status_result(cpu,
			host_prepare_monitor_status_raw_bridge);
}

static unsigned long host_map_memory_raw_bridge(void *os, unsigned long phys,
						unsigned long size)
{
	return ihk_mc_map_memory(os, phys, size);
}

static unsigned long host_map_memory_bridge(void *os, unsigned long phys,
					    unsigned long size)
{
	return host_map_memory_result(os, phys, size,
			host_map_memory_raw_bridge);
}

static void *host_prepare_map_virtual_raw_bridge(unsigned long phys, int npages,
						 unsigned long attr)
{
	return ihk_mc_map_virtual(phys, npages,
				(enum ihk_mc_pt_attribute)attr);
}

static void *host_prepare_map_virtual_bridge(unsigned long phys, int npages,
					     unsigned long attr)
{
	return host_prepare_map_virtual_result(phys, npages, attr,
			host_prepare_map_virtual_raw_bridge);
}

static void host_unmap_virtual_raw_bridge(void *addr, int npages)
{
	ihk_mc_unmap_virtual(addr, npages);
}

static void host_unmap_virtual_bridge(void *addr, int npages)
{
	host_unmap_virtual_result(addr, npages,
			host_unmap_virtual_raw_bridge);
}

static void host_unmap_memory_raw_bridge(void *os, unsigned long phys,
					 unsigned long size)
{
	ihk_mc_unmap_memory(os, phys, size);
}

static void host_unmap_memory_bridge(void *os, unsigned long phys,
				     unsigned long size)
{
	host_unmap_memory_result(os, phys, size,
			host_unmap_memory_raw_bridge);
}

static void host_prepare_free_raw_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void host_prepare_free_bridge(void *ptr)
{
	host_prepare_free_result(ptr, host_prepare_free_raw_bridge);
}

static void *host_prepare_alloc_raw_bridge(unsigned long size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void *host_prepare_alloc_bridge(unsigned long size, unsigned long flags)
{
	return host_prepare_alloc_result(size, flags,
			host_prepare_alloc_raw_bridge);
}

static void host_prepare_copy_long_raw_bridge(void *dst, const void *src,
					      unsigned long size)
{
	memcpy_long(dst, src, size);
}

static void host_prepare_copy_long_bridge(void *dst, const void *src,
					  unsigned long size)
{
	host_prepare_copy_long_result(dst, src, size,
			host_prepare_copy_long_raw_bridge);
}

static void *host_prepare_create_thread_raw_bridge(unsigned long entry,
						   unsigned long *cpu_set,
						   unsigned long cpu_set_size)
{
	return create_thread(entry, cpu_set, cpu_set_size);
}

static void *host_prepare_create_thread_bridge(unsigned long entry,
					       unsigned long *cpu_set,
					       unsigned long cpu_set_size)
{
	return host_create_thread_result(entry, cpu_set, cpu_set_size,
			host_prepare_create_thread_raw_bridge);
}

static void host_prepare_destroy_thread_raw_bridge(void *thread)
{
	destroy_thread((struct thread *)thread);
}

static void host_prepare_destroy_thread_bridge(void *thread)
{
	host_destroy_thread_result(thread, host_prepare_destroy_thread_raw_bridge);
}

static int host_prepare_ranges_raw_bridge(void *thread,
					  struct program_load_desc *pn,
					  struct program_load_desc *p,
					  unsigned long attr,
					  char *args, int args_len,
					  char *envs, int envs_len)
{
	return prepare_process_ranges_args_envs((struct thread *)thread, pn, p,
			(enum ihk_mc_pt_attribute)attr, args, args_len, envs,
			envs_len);
}

static int host_prepare_ranges_bridge(void *thread,
				      struct program_load_desc *pn,
				      struct program_load_desc *p,
				      unsigned long attr,
				      char *args, int args_len,
				      char *envs, int envs_len)
{
	return host_prepare_ranges_result(thread, pn, p, attr, args, args_len,
			envs, envs_len, host_prepare_ranges_raw_bridge);
}

static int host_prepare_nr_numa_nodes_raw_bridge(void)
{
	return ihk_mc_get_nr_numa_nodes();
}

static int host_prepare_nr_numa_nodes_bridge(void)
{
	return host_nr_numa_nodes_result(host_prepare_nr_numa_nodes_raw_bridge);
}

static void host_prepare_flush_tlb_raw_bridge(void)
{
	flush_tlb();
}

static void host_prepare_flush_tlb_bridge(void)
{
	host_flush_tlb_result(host_prepare_flush_tlb_raw_bridge);
}

#ifdef ENABLE_TOFU
extern void tof_utofu_finalize(void);

static void host_prepare_tofu_finalize_raw_bridge(void)
{
	tof_utofu_finalize();
}

static void host_prepare_tofu_finalize_bridge(void)
{
	host_tofu_finalize_result(host_prepare_tofu_finalize_raw_bridge);
}
#endif

static void host_prepare_process_log_raw_bridge(int event, unsigned long arg0,
						unsigned long arg1,
						unsigned long arg2)
{
	switch (event) {
	case HOST_PREPARE_LOG_BROKEN_DESC:
		kprintf("%s: broken mcexec program_load_desc\n", __func__);
		break;
	case HOST_PREPARE_LOG_INVALID_SECTIONS:
		kprintf("%s: ERROR: ELF sections other than 1 to 16 ??\n",
			__FUNCTION__);
		break;
	case HOST_PREPARE_LOG_NUM_SECTIONS:
		dkprintf("# of sections: %lu\n", arg0);
		break;
	case HOST_PREPARE_LOG_NUMA_BIND_ERROR:
	case HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR:
		kprintf("%s: error: NUMA id %lu is larger than mask size!\n",
			__FUNCTION__, arg0);
		break;
	case HOST_PREPARE_LOG_NUMA_POLICY:
		dkprintf("%s: numa_mem_policy: %lu, numa_mask: %lu\n",
			 __func__, arg0, arg1);
		break;
	case HOST_PREPARE_LOG_PID_FLAGS:
		dkprintf("%s: PID: %lu, flags: 0x%lx\n",
			__func__, arg0, arg1);
		break;
	case HOST_PREPARE_LOG_RLIMIT:
		dkprintf("%s: rlim_cur: %ld, rlim_max: %ld, stack_premap: %ld\n",
				__FUNCTION__, arg0, arg1, arg2);
		break;
	case HOST_PREPARE_LOG_PREPARE_ERROR:
		kprintf("error: preparing process ranges, args, envs, stack\n");
		break;
	case HOST_PREPARE_LOG_NEW_PROCESS:
		dkprintf("new process : %p [%lu] / table : %p\n",
			(void *)arg0, arg1, (void *)arg2);
		break;
	}
}

static void host_prepare_process_log_bridge(int event, unsigned long arg0,
					    unsigned long arg1,
					    unsigned long arg2)
{
	host_prepare_process_log_result(event, arg0, arg1, arg2,
			host_prepare_process_log_raw_bridge);
}

static int process_msg_prepare_process(unsigned long rphys)
{
	return host_prepare_process_body_result(rphys, num_processors,
			PTATTR_NO_EXECUTE | PTATTR_WRITABLE | PTATTR_FOR_USER,
			PAGE_SIZE, IHK_MC_AP_NOWAIT, USER_END,
			LD_TASK_UNMAPPED_BASE, SIGCHLD, MPOL_MAX, MPOL_BIND,
			host_prepare_monitor_status_bridge,
			host_map_memory_bridge, host_prepare_map_virtual_bridge,
			host_unmap_virtual_bridge, host_unmap_memory_bridge,
			host_prepare_alloc_bridge, host_prepare_free_bridge,
			host_prepare_copy_long_bridge,
			host_prepare_create_thread_bridge,
			host_prepare_destroy_thread_bridge,
			host_prepare_ranges_bridge,
			host_prepare_nr_numa_nodes_bridge,
			host_prepare_flush_tlb_bridge,
#ifdef ENABLE_TOFU
			host_prepare_tofu_finalize_bridge,
#else
			NULL,
#endif
			host_prepare_process_log_bridge);
}

static void syscall_channel_send(struct ihk_ikc_channel_desc *c,
                                 struct ikc_scd_packet *packet)
{
	ihk_ikc_send(c, packet, 0);
}

static void host_ikc_packet_send_raw_bridge(void *channel,
					    struct ikc_scd_packet *packet)
{
	syscall_channel_send((struct ihk_ikc_channel_desc *)channel, packet);
}

static void *host_map_virtual_raw_bridge(unsigned long phys, int npages, int attr)
{
	return ihk_mc_map_virtual(phys, npages,
			(enum ihk_mc_pt_attribute)attr);
}

static void *host_map_virtual_bridge(unsigned long phys, int npages, int attr)
{
	return host_map_virtual_result(phys, npages, attr,
			host_map_virtual_raw_bridge);
}

static int host_cpu_read_write_register_raw_bridge(void *desc, int op)
{
	return arch_cpu_read_write_register(
			(struct ihk_os_cpu_register *)desc,
			(enum mcctrl_os_cpu_operation)op);
}

static int host_cpu_read_write_register_bridge(void *desc, int op)
{
	return host_cpu_rw_register_result(desc, op,
			host_cpu_read_write_register_raw_bridge);
}

static void host_cleanup_process_log_raw_bridge(int pid,
						unsigned long thread_arg)
{
	dkprintf("SCD_MSG_CLEANUP_PROCESS pid=%d, thread=0x%llx\n",
			pid, thread_arg);
}

static void host_cleanup_process_log_bridge(int pid, unsigned long thread_arg)
{
	host_cleanup_process_log_result(pid, thread_arg,
			host_cleanup_process_log_raw_bridge);
}

static void host_terminate_host_raw_bridge(int pid, void *thread)
{
	terminate_host(pid, (struct thread *)thread);
}

static void host_terminate_host_bridge(int pid, void *thread)
{
	host_terminate_host_result(pid, thread,
			host_terminate_host_raw_bridge);
}

static void host_cleanup_fd_log_raw_bridge(int pid, unsigned long fd, int err)
{
	dkprintf("SCD_MSG_CLEANUP_FD pid=%d, fd=%d -> err: %d\n",
			pid, (int)fd, err);
}

static void host_cleanup_fd_log_bridge(int pid, unsigned long fd, int err)
{
	host_cleanup_fd_log_result(pid, fd, err,
			host_cleanup_fd_log_raw_bridge);
}

extern unsigned long do_kill(struct thread *, int, int, int, struct siginfo *, int ptracecont);
extern void debug_log(long);

static unsigned long host_do_kill_raw_bridge(int pid, int tid, int sig,
					     void *info)
{
	return do_kill(NULL, pid, tid, sig, (struct siginfo *)info, 0);
}

static unsigned long host_do_kill_bridge(int pid, int tid, int sig, void *info)
{
	return host_do_kill_result(pid, tid, sig, info,
			host_do_kill_raw_bridge);
}

static void host_send_signal_log_raw_bridge(int pid, int tid, int sig, int rc)
{
#ifndef ENABLE_FUGAKU_HACKS
	dkprintf("SCD_MSG_SEND_SIGNAL: do_kill(pid=%d, tid=%d, sig=%d)=%d\n",
			pid, tid, sig, rc);
#else
	kprintf("SCD_MSG_SEND_SIGNAL: do_kill(pid=%d, tid=%d, sig=%d)=%d\n",
			pid, tid, sig, rc);
#endif
}

static void host_send_signal_log_bridge(int pid, int tid, int sig, int rc)
{
	host_send_signal_log_result(pid, tid, sig, rc,
			host_send_signal_log_raw_bridge);
}

static void *host_find_thread_raw_bridge(int pid, int tid)
{
	return find_thread(pid, tid);
}

static void *host_find_thread_bridge(int pid, int tid)
{
	return host_find_thread_result(pid, tid, host_find_thread_raw_bridge);
}

static void host_wakeup_scd_waitq_raw_bridge(void *thread)
{
	waitq_wakeup(&((struct thread *)thread)->scd_wq);
}

static void host_wakeup_scd_waitq_bridge(void *thread)
{
	host_wakeup_thread_result(thread, host_wakeup_scd_waitq_raw_bridge);
}

static void host_thread_unlock_raw_bridge(void *thread)
{
	thread_unlock((struct thread *)thread);
}

static void host_thread_unlock_bridge(void *thread)
{
	host_thread_unlock_result(thread, host_thread_unlock_raw_bridge);
}

static void host_wake_syscall_log_raw_bridge(int tid, int found)
{
	if (!found) {
		kprintf("%s: WARNING: no thread for SCD reply? TID: %d\n",
			"syscall_packet_handler", tid);
		return;
	}

	dkprintf("%s: SCD_MSG_WAKE_UP_SYSCALL_THREAD: waking up tid %d\n",
		"syscall_packet_handler", tid);
}

static void host_wake_syscall_log_bridge(int tid, int found)
{
	host_wake_syscall_log_result(tid, found,
			host_wake_syscall_log_raw_bridge);
}

static void host_debug_log_raw_bridge(unsigned long code)
{
	debug_log(code);
}

static void host_debug_log_bridge(unsigned long code)
{
	host_debug_log_result(code, host_debug_log_raw_bridge);
}

static void host_debug_log_print_raw_bridge(unsigned long code)
{
	dkprintf("SCD_MSG_DEBUG_LOG code=%lx\n", code);
}

static void host_debug_log_print_bridge(unsigned long code)
{
	host_debug_log_print_result(code, host_debug_log_print_raw_bridge);
}

static int host_thread_profile_enabled_raw_bridge(void *thread)
{
#ifdef PROFILE_ENABLE
	return ((struct thread *)thread)->profile;
#else
	(void)thread;
	return 0;
#endif
}

static int host_thread_profile_enabled_bridge(void *thread)
{
	return host_thread_profile_enabled_result(thread,
			host_thread_profile_enabled_raw_bridge);
}

static unsigned long host_timestamp_raw_bridge(void)
{
#ifdef PROFILE_ENABLE
	return rdtsc();
#else
	return 0;
#endif
}

static unsigned long host_timestamp_bridge(void)
{
	return host_timestamp_result(host_timestamp_raw_bridge);
}

static void host_preempt_disable_raw_bridge(void)
{
	preempt_disable();
}

static void host_preempt_disable_bridge(void)
{
	host_preempt_result(host_preempt_disable_raw_bridge);
}

static void host_preempt_enable_raw_bridge(void)
{
	preempt_enable();
}

static void host_preempt_enable_bridge(void)
{
	host_preempt_result(host_preempt_enable_raw_bridge);
}

static void host_remote_page_fault_process_raw_bridge(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason)
{
	page_fault_process_vm(((struct thread *)thread)->vm,
			      (void *)fault_address, fault_reason);
}

static void host_remote_page_fault_process_bridge(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason)
{
	host_remote_page_fault_process_result(thread, fault_address,
			fault_reason, host_remote_page_fault_process_raw_bridge);
}

static void host_remote_page_fault_profile_event_raw_bridge(
		int event, unsigned long delta)
{
#ifdef PROFILE_ENABLE
	profile_event_add((enum profile_event_type)event, delta);
#else
	(void)event;
	(void)delta;
#endif
}

static void host_remote_page_fault_profile_event_bridge(int event,
							unsigned long delta)
{
	host_profile_event_result(event, delta,
			host_remote_page_fault_profile_event_raw_bridge);
}

static void host_remote_page_fault_log_raw_bridge(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason)
{
	dkprintf("remote page fault,pid=%d,va=%lx,reason=%lx\n",
		 ((struct thread *)thread)->proc->pid, fault_address,
		 fault_reason);
}

static void host_remote_page_fault_log_bridge(void *thread,
					      unsigned long fault_address,
					      unsigned long fault_reason)
{
	host_remote_page_fault_log_result(thread, fault_address, fault_reason,
			host_remote_page_fault_log_raw_bridge);
}

static void *host_alloc_raw_bridge(unsigned long size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void *host_alloc_bridge(unsigned long size, unsigned long flags)
{
	return host_alloc_result(size, flags, host_alloc_raw_bridge);
}

static int host_ikc_connect_raw_bridge(struct ihk_ikc_connect_param *param)
{
	return ihk_ikc_connect(NULL, param);
}

static void host_delay_raw_bridge(unsigned long usec)
{
	ihk_mc_delay_us(usec);
}

static void host_set_current_ikc2linux_raw_bridge(void *channel)
{
	get_this_cpu_local_var()->ikc2linux =
		(struct ihk_ikc_channel_desc *)channel;
}

static void host_set_regular_channel_raw_bridge(void *channel, int cpu)
{
	ihk_ikc_set_regular_channel(NULL,
			(struct ihk_ikc_channel_desc *)channel, cpu);
}

static void host_panic_raw_bridge(void)
{
	panic("");
}

static void host_init_ikc2linux_log_raw_bridge(int event)
{
	switch (event) {
	case HOST_INIT_IKC_LOG_ALLOC_ERROR:
		kprintf("%s: error: allocating Linux channels\n",
				"init_host_ikc2linux");
		break;
	case HOST_INIT_IKC_LOG_TRY_CONNECT:
		dkprintf("(ikc2linux) Trying to connect host ...");
		break;
	case HOST_INIT_IKC_LOG_RETRY_DOT:
		dkprintf(".");
		break;
	case HOST_INIT_IKC_LOG_CONNECTED:
		dkprintf("connected.\n");
		break;
	}
}

static void host_init_ikc2mckernel_log_raw_bridge(int event)
{
	switch (event) {
	case HOST_INIT_IKC_LOG_TRY_CONNECT:
		dkprintf("(ikc2mckernel) Trying to connect host ...");
		break;
	case HOST_INIT_IKC_LOG_RETRY_DOT:
		dkprintf(".");
		break;
	case HOST_INIT_IKC_LOG_CONNECTED:
		dkprintf("connected.\n");
		break;
	}
}

static void host_packet_copy_raw_bridge(void *dst, struct ikc_scd_packet *src,
					unsigned long size)
{
	memcpy(dst, src, size);
}

static void host_packet_copy_bridge(void *dst, struct ikc_scd_packet *src,
				    unsigned long size)
{
	host_packet_copy_result(dst, src, size, host_packet_copy_raw_bridge);
}

static void host_remote_page_fault_defer_raw_bridge(
		void *thread, void *arg, host_backlog_fn_t backlog_fn)
{
	((struct thread *)thread)->rpf_arg = arg;
	((struct thread *)thread)->rpf_backlog = backlog_fn;
}

static void host_remote_page_fault_defer_bridge(void *thread, void *arg,
						host_backlog_fn_t backlog_fn)
{
	host_remote_page_fault_defer_result(thread, arg, backlog_fn,
			host_remote_page_fault_defer_raw_bridge);
}

static int host_sched_wakeup_thread_raw_bridge(void *thread, int valid_states)
{
	return sched_wakeup_thread((struct thread *)thread, valid_states);
}

static int host_sched_wakeup_thread_bridge(void *thread, int valid_states)
{
	return host_sched_wakeup_result(thread, valid_states,
			host_sched_wakeup_thread_raw_bridge);
}

static void host_remote_page_fault_missing_log_raw_bridge(int tid)
{
	kprintf("%s: WARNING: no thread for remote pf %d\n", __func__, tid);
}

static void host_remote_page_fault_missing_log_bridge(int tid)
{
	host_remote_page_fault_missing_log_result(tid,
			host_remote_page_fault_missing_log_raw_bridge);
}

static void *host_schedule_thread_proc_raw_bridge(void *thread)
{
	return ((struct thread *)thread)->proc;
}

static void *host_schedule_thread_proc_bridge(void *thread)
{
	return host_thread_proc_result(thread,
			host_schedule_thread_proc_raw_bridge);
}

static int host_schedule_current_cpu_raw_bridge(void)
{
	return ihk_mc_get_processor_id();
}

static int host_schedule_current_cpu_bridge(void)
{
	return host_current_cpu_result(host_schedule_current_cpu_raw_bridge);
}

static int host_schedule_cpu_allowed_raw_bridge(void *thread, int cpuid)
{
	return CPU_ISSET(cpuid, &((struct thread *)thread)->cpu_set);
}

static int host_schedule_cpu_allowed_bridge(void *thread, int cpuid)
{
	return host_thread_cpu_allowed_result(thread, cpuid,
			host_schedule_cpu_allowed_raw_bridge);
}

static int host_schedule_obtain_cpuid_raw_bridge(void *thread)
{
	return obtain_clone_cpuid(&((struct thread *)thread)->cpu_set, 0);
}

static int host_schedule_obtain_cpuid_bridge(void *thread)
{
	return host_thread_obtain_cpuid_result(thread,
			host_schedule_obtain_cpuid_raw_bridge);
}

static int host_schedule_proc_pid_raw_bridge(void *proc)
{
	return ((struct process *)proc)->pid;
}

static int host_schedule_proc_pid_bridge(void *proc)
{
	return host_proc_pid_result(proc, host_schedule_proc_pid_raw_bridge);
}

static unsigned long host_schedule_thread_pc_raw_bridge(void *thread)
{
	struct thread *t = thread;

	return t->uctx ? ihk_mc_syscall_pc(t->uctx) : 0UL;
}

static unsigned long host_schedule_thread_pc_bridge(void *thread)
{
	return host_thread_reg_result(thread, host_schedule_thread_pc_raw_bridge);
}

static unsigned long host_schedule_thread_sp_raw_bridge(void *thread)
{
	struct thread *t = thread;

	return t->uctx ? ihk_mc_syscall_sp(t->uctx) : 0UL;
}

static unsigned long host_schedule_thread_sp_bridge(void *thread)
{
	return host_thread_reg_result(thread, host_schedule_thread_sp_raw_bridge);
}

static void host_schedule_invalid_log_raw_bridge(void *thread)
{
	kprintf("mcexec_v10: schedule_process invalid thread=%p\n", thread);
}

static void host_schedule_invalid_log_bridge(void *thread)
{
	host_schedule_invalid_log_result(thread,
			host_schedule_invalid_log_raw_bridge);
}

static void host_schedule_received_log_raw_bridge(void *thread, int pid,
						 unsigned long pc,
						 unsigned long sp, int cpuid)
{
	kprintf("mcexec_v10: schedule_process received thread=%p pid=%d entry=0x%lx sp=0x%lx current_cpu=%d\n",
		thread, pid, pc, sp, cpuid);
}

static void host_schedule_received_log_bridge(void *thread, int pid,
					     unsigned long pc,
					     unsigned long sp, int cpuid)
{
	host_schedule_received_log_result(thread, pid, pc, sp, cpuid,
			host_schedule_received_log_raw_bridge);
}

static void host_schedule_no_cpu_log_raw_bridge(void)
{
	kprintf("No CPU available\n");
}

static void host_schedule_no_cpu_log_bridge(void)
{
	host_schedule_no_cpu_log_result(host_schedule_no_cpu_log_raw_bridge);
}

static void host_schedule_set_tid_raw_bridge(void *thread, int tid)
{
	((struct thread *)thread)->tid = tid;
}

static void host_schedule_set_tid_bridge(void *thread, int tid)
{
	host_thread_set_tid_result(thread, tid,
			host_schedule_set_tid_raw_bridge);
}

static void host_schedule_set_proc_status_raw_bridge(void *proc, int status)
{
	((struct process *)proc)->status = status;
}

static void host_schedule_set_proc_status_bridge(void *proc, int status)
{
	host_status_set_result(proc, status,
			host_schedule_set_proc_status_raw_bridge);
}

static void host_schedule_set_thread_status_raw_bridge(void *thread, int status)
{
	((struct thread *)thread)->status = status;
}

static void host_schedule_set_thread_status_bridge(void *thread, int status)
{
	host_status_set_result(thread, status,
			host_schedule_set_thread_status_raw_bridge);
}

static void host_schedule_chain_thread_raw_bridge(void *thread)
{
	chain_thread(thread);
}

static void host_schedule_chain_thread_bridge(void *thread)
{
	host_chain_thread_result(thread, host_schedule_chain_thread_raw_bridge);
}

static void host_schedule_chain_process_raw_bridge(void *proc)
{
	chain_process(proc);
}

static void host_schedule_chain_process_bridge(void *proc)
{
	host_chain_process_result(proc, host_schedule_chain_process_raw_bridge);
}

static void host_schedule_runq_add_raw_bridge(void *thread, int cpuid)
{
	runq_add_thread(thread, cpuid);
}

static void host_schedule_runq_add_bridge(void *thread, int cpuid)
{
	host_runq_add_thread_result(thread, cpuid,
			host_schedule_runq_add_raw_bridge);
}

static void host_schedule_queued_log_raw_bridge(int pid, int tid, int cpuid,
						int status)
{
	kprintf("mcexec_v10: schedule_process queued pid=%d tid=%d cpu=%d status=%d\n",
		pid, tid, cpuid, status);
}

static void host_schedule_queued_log_bridge(int pid, int tid, int cpuid,
					    int status)
{
	host_schedule_queued_log_result(pid, tid, cpuid, status,
			host_schedule_queued_log_raw_bridge);
}

static int host_perf_init_raw_bridge(int counter, unsigned int config, int mode)
{
	return host_perf_init_raw_result(counter, config, mode,
			ihk_mc_perfctr_init_raw);
}

static int host_perf_stop_bridge(unsigned long counter_mask, int flags)
{
	return host_perf_stop_result(counter_mask, flags, ihk_mc_perfctr_stop);
}

static int host_perf_reset_bridge(int counter)
{
	return host_perf_reset_result(counter, ihk_mc_perfctr_reset);
}

static int host_perf_start_bridge(unsigned long counter_mask)
{
	return host_perf_start_result(counter_mask, ihk_mc_perfctr_start);
}

static unsigned long host_perf_read_bridge(int counter)
{
	return host_perf_read_result(counter, ihk_mc_perfctr_read);
}

static void host_perf_unexpected_ctrl_type_raw_bridge(void)
{
	kprintf("%s: SCD_MSG_PERF_CTRL unexpected ctrl_type\n", __FUNCTION__);
}

static void host_perf_unexpected_ctrl_type_bridge(void)
{
	host_perf_unexpected_result(host_perf_unexpected_ctrl_type_raw_bridge);
}

extern int process_cleanup_before_terminate(int pid);
extern int process_cleanup_fd(int pid, int fd);

static int host_cleanup_process_raw_bridge(int pid)
{
	return process_cleanup_before_terminate(pid);
}

static int host_cleanup_process_bridge(int pid)
{
	return host_cleanup_process_result(pid,
			host_cleanup_process_raw_bridge);
}

static int host_cleanup_fd_raw_bridge(int pid, int fd)
{
	return process_cleanup_fd(pid, fd);
}

static int host_cleanup_fd_bridge(int pid, int fd)
{
	return host_cleanup_fd_result(pid, fd, host_cleanup_fd_raw_bridge);
}

static void host_init_channel_acked_log_print_bridge(void)
{
	dkprintf("SCD_MSG_INIT_CHANNEL_ACKED\n");
}

static void host_init_channel_acked_log_bridge(void)
{
	host_init_ack_log_result(host_init_channel_acked_log_print_bridge);
}

static void host_schedule_process_log_print_bridge(unsigned long arg)
{
	dkprintf("SCD_MSG_SCHEDULE_PROCESS: %lx\n", arg);
}

static void host_schedule_process_log_bridge(struct ikc_scd_packet *packet)
{
	host_schedule_process_log_result(packet,
			host_schedule_process_log_print_bridge);
}

static int host_procfs_request_bridge(struct ikc_scd_packet *packet)
{
	return host_procfs_request_result(packet, process_procfs_request);
}

static void host_sysfs_packet_handler_bridge(void *channel, int msg, int err,
					     long arg1, long arg2, long arg3)
{
	sysfss_packet_handler((struct ihk_ikc_channel_desc *)channel, msg, err,
			      arg1, arg2, arg3);
}

static void host_sysfs_packet_bridge(void *channel, int msg, int err,
				     long arg1, long arg2, long arg3)
{
	host_sysfs_packet_result(channel, msg, err, arg1, arg2, arg3,
			host_sysfs_packet_handler_bridge);
}

static void host_unknown_packet_log_print_bridge(struct ikc_scd_packet *packet)
{
	kprintf("syscall_pakcet_handler:unknown message "
			"(%d.%d.%d.%d.%d.%#lx)\n",
			packet->msg, packet->ref, packet->osnum, packet->pid,
			packet->err, packet->arg);
}

static void host_unknown_packet_log_bridge(struct ikc_scd_packet *packet)
{
	host_unknown_packet_log_result(packet,
			host_unknown_packet_log_print_bridge);
}

static void host_release_packet_raw_bridge(struct ikc_scd_packet *packet)
{
	ihk_ikc_release_packet((struct ihk_ikc_free_packet *)packet);
}

static void host_release_packet_bridge(struct ikc_scd_packet *packet)
{
	host_release_packet_result(packet, host_release_packet_raw_bridge);
}

static void *host_current_ikc2linux_raw_bridge(void)
{
	return get_this_cpu_local_var()->ikc2linux;
}

static void *host_current_thread_raw_bridge(void)
{
	return get_this_cpu_local_var()->current;
}

void send_procfs_answer(struct ikc_scd_packet *packet, int err)
{
	host_procfs_answer_current_result(packet, err,
			host_current_ikc2linux_raw_bridge,
			host_ikc_packet_send_raw_bridge);
}

static void do_remote_page_fault(struct ikc_scd_packet *packet, int err)
{
	int profile_event = 0;
#ifdef PROFILE_ENABLE
	profile_event = PROFILE_remote_page_fault;
#endif

	host_remote_page_fault_current_result(packet, err, PF_POPULATE,
			profile_event, host_current_ikc2linux_raw_bridge,
			host_current_thread_raw_bridge,
			host_thread_profile_enabled_bridge,
			host_timestamp_bridge,
			host_preempt_disable_bridge,
			host_remote_page_fault_process_bridge,
			host_preempt_enable_bridge,
			host_remote_page_fault_profile_event_bridge,
			host_remote_page_fault_log_bridge,
			host_ikc_packet_send_raw_bridge);
}

static void remote_page_fault(void *arg)
{
	do_remote_page_fault(arg, 0);
}

static int host_prepare_process_raw_bridge(unsigned long rphys)
{
	return process_msg_prepare_process(rphys);
}

static int host_prepare_process_bridge(unsigned long rphys)
{
	return host_prepare_process_result(rphys,
			host_prepare_process_raw_bridge);
}

static int host_prepare_process_request_bridge(void *response_channel,
					       struct ikc_scd_packet *packet)
{
	return host_prepare_process_request_result(response_channel, packet,
			host_prepare_process_bridge,
			host_ikc_packet_send_raw_bridge);
}

static int host_schedule_process_request_bridge(struct ikc_scd_packet *packet)
{
	host_schedule_process_log_bridge(packet);
	return host_schedule_process_request_result(packet,
			host_schedule_thread_proc_bridge,
			host_schedule_current_cpu_bridge,
			host_schedule_cpu_allowed_bridge,
			host_schedule_obtain_cpuid_bridge,
			host_schedule_proc_pid_bridge,
			host_schedule_thread_pc_bridge,
			host_schedule_thread_sp_bridge,
			host_schedule_invalid_log_bridge,
			host_schedule_received_log_bridge,
			host_schedule_no_cpu_log_bridge,
			host_schedule_set_tid_bridge,
			host_schedule_set_proc_status_bridge,
			host_schedule_set_thread_status_bridge,
			host_schedule_chain_thread_bridge,
			host_schedule_chain_process_bridge,
			host_schedule_runq_add_bridge,
			host_schedule_queued_log_bridge, PS_RUNNING);
}

static int host_wake_syscall_thread_request_bridge(
		struct ikc_scd_packet *packet)
{
	return host_wake_syscall_thread_request_result(packet,
			host_find_thread_bridge,
			host_wakeup_scd_waitq_bridge,
			host_thread_unlock_bridge,
			host_wake_syscall_log_bridge);
}

static int host_remote_page_fault_request_bridge(struct ikc_scd_packet *packet,
						 void *current_thread)
{
	return host_remote_page_fault_request_result(packet,
			host_find_thread_bridge, current_thread,
			do_remote_page_fault,
			host_alloc_bridge, host_packet_copy_bridge,
			host_remote_page_fault_defer_bridge,
			host_sched_wakeup_thread_bridge,
			host_thread_unlock_bridge,
			host_remote_page_fault_missing_log_bridge,
			remote_page_fault, sizeof(struct ikc_scd_packet),
			IHK_MC_AP_NOWAIT, PS_INTERRUPTIBLE);
}

static int host_send_signal_request_bridge(void *response_channel,
					   struct ikc_scd_packet *packet)
{
	host_send_signal_request_result(response_channel, packet,
			host_map_memory_bridge, host_map_virtual_bridge,
			host_unmap_virtual_bridge, host_unmap_memory_bridge,
			host_do_kill_bridge, host_send_signal_log_bridge,
			host_ikc_packet_send_raw_bridge);
	return 0;
}

static int host_cleanup_process_request_bridge(void *response_channel,
					       struct ikc_scd_packet *packet)
{
	host_cleanup_process_request_result(response_channel, packet,
			host_cleanup_process_bridge,
			host_terminate_host_bridge,
			host_cleanup_process_log_bridge,
			host_ikc_packet_send_raw_bridge);
	return 0;
}

static int host_cleanup_fd_request_bridge(void *response_channel,
					  struct ikc_scd_packet *packet)
{
	host_cleanup_fd_request_result(response_channel, packet,
			host_cleanup_fd_bridge, host_cleanup_fd_log_bridge,
			host_ikc_packet_send_raw_bridge);
	return 0;
}

static int host_debug_log_request_bridge(struct ikc_scd_packet *packet)
{
	return host_debug_log_request_result(packet, host_debug_log_bridge,
			host_debug_log_print_bridge);
}

static int host_perf_ctrl_request_bridge(void *response_channel,
					 struct ikc_scd_packet *packet)
{
	return host_perf_ctrl_request_result(response_channel, packet,
			host_map_memory_bridge, host_map_virtual_bridge,
			host_unmap_virtual_bridge, host_unmap_memory_bridge,
			host_perf_init_raw_bridge,
			host_perf_stop_bridge, host_perf_reset_bridge,
			host_perf_start_bridge, host_perf_read_bridge,
			host_perf_unexpected_ctrl_type_bridge,
			host_ikc_packet_send_raw_bridge);
}

static int host_cpu_rw_reg_request_bridge(void *response_channel,
					  struct ikc_scd_packet *packet)
{
	host_cpu_rw_reg_request_result(response_channel, packet,
			host_map_memory_bridge, host_map_virtual_bridge,
			host_unmap_virtual_bridge, host_unmap_memory_bridge,
			host_cpu_read_write_register_bridge,
			host_ikc_packet_send_raw_bridge);
	return 0;
}

static const struct host_scd_dispatch_ops host_scd_dispatch_ops = {
	.init_ack_log_fn = host_init_channel_acked_log_bridge,
	.prepare_process_fn = host_prepare_process_request_bridge,
	.schedule_process_fn = host_schedule_process_request_bridge,
	.wake_syscall_thread_fn = host_wake_syscall_thread_request_bridge,
	.remote_page_fault_fn = host_remote_page_fault_request_bridge,
	.send_signal_fn = host_send_signal_request_bridge,
	.procfs_request_fn = host_procfs_request_bridge,
	.cleanup_process_fn = host_cleanup_process_request_bridge,
	.cleanup_fd_fn = host_cleanup_fd_request_bridge,
	.debug_log_fn = host_debug_log_request_bridge,
	.sysfs_packet_fn = host_sysfs_packet_bridge,
	.perf_ctrl_fn = host_perf_ctrl_request_bridge,
	.cpu_rw_reg_fn = host_cpu_rw_reg_request_bridge,
	.unknown_packet_log_fn = host_unknown_packet_log_bridge,
	.release_packet_fn = host_release_packet_bridge,
};

static int syscall_packet_handler(struct ihk_ikc_channel_desc *c,
	                                  void *__packet, void *ihk_os)
{
	int profile_event = 0;

#ifdef PROFILE_ENABLE
	profile_event = PROFILE_remote_page_fault;
#endif

	return host_syscall_packet_handler_result(c, __packet, ihk_os,
			&host_scd_dispatch_ops, host_current_ikc2linux_raw_bridge,
			host_current_thread_raw_bridge, PF_POPULATE,
			profile_event, sizeof(struct ikc_scd_packet),
			IHK_MC_AP_NOWAIT, PS_INTERRUPTIBLE, PS_RUNNING);
}

static int dummy_packet_handler(struct ihk_ikc_channel_desc *c,
                                  void *__packet, void *__os)
{
	return host_dummy_packet_handler_result(c, __packet, __os,
			host_release_packet_bridge);
}

void init_host_ikc2linux(int linux_cpu)
{
	host_init_ikc2linux_public_result(linux_cpu, &ikc2linuxs,
			ihk_mc_get_nr_linux_cores(), num_processors,
			sizeof(struct ikc_scd_packet), PAGE_SIZE,
			IHK_MC_AP_NOWAIT, host_alloc_raw_bridge,
			host_ikc_connect_raw_bridge, host_delay_raw_bridge,
			host_set_current_ikc2linux_raw_bridge,
			dummy_packet_handler, host_init_ikc2linux_log_raw_bridge,
			host_panic_raw_bridge);
}

void init_host_ikc2mckernel(void)
{
	host_init_ikc2mckernel_public_result(sizeof(struct ikc_scd_packet),
			PAGE_SIZE, ihk_ikc_get_processor_id(),
			syscall_packet_handler, host_ikc_connect_raw_bridge,
			host_delay_raw_bridge, host_set_regular_channel_raw_bridge,
			host_init_ikc2mckernel_log_raw_bridge,
			host_panic_raw_bridge);
}
