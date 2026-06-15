/**
 * \file procfs.c
 *  License details are found in the file LICENSE.
 * \brief
 *  McKernel procfs
 * \author Naoki Hamada <nao@axe.bz> \par
 * 	Copyright (C) 2014  AXE, Inc.
 */
/*
 * HISTORY:
 */
/* procfs.c COPYRIGHT FUJITSU LIMITED 2015-2017 */

#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <ihk/mm.h>
#include <ihk/debug.h>
#include <ihk/ikc.h>
#include <ikc/master.h>
#include <cls.h>
#include <syscall.h>
#include <kmalloc.h>
#include <process.h>
#include <page.h>
#include <mman.h>
#include <bitmap.h>
#include <init.h>
#include <object_helpers.h>

//#define DEBUG_PRINT_PROCFS

#ifdef DEBUG_PRINT_PROCFS
#define	dprintf(...) kprintf(__VA_ARGS__)
#else
#define dprintf(...)
#endif

extern int snprintf(char *buf, size_t size, const char *fmt, ...);
extern int sscanf(const char * buf, const char * fmt, ...);
extern int scnprintf(char * buf, size_t size, const char *fmt, ...);
static int do_procfs_backlog(void *arg);

struct mckernel_procfs_buffer {
	unsigned long next_pa;
	unsigned long pos;
	unsigned long size;
	char buf[0];
};

#define PA_NULL (-1L)

static unsigned long procfs_buf_phys_bridge(struct mckernel_procfs_buffer *pbuf);

static void *procfs_buf_page_alloc_bridge(int npages, unsigned long flags)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

static struct mckernel_procfs_buffer *buf_alloc(unsigned long *phys, long pos)
{
	return procfs_buf_alloc_result(phys, pos, procfs_buf_page_alloc_bridge,
			procfs_buf_phys_bridge, IHK_MC_AP_NOWAIT);
}

static struct mckernel_procfs_buffer *procfs_buf_phys_to_virt_bridge(
		unsigned long phys)
{
	return phys_to_virt(phys);
}

static void procfs_buf_free_page_bridge(struct mckernel_procfs_buffer *pbuf)
{
	_ihk_mc_free_pages(pbuf, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

static unsigned long procfs_buf_phys_bridge(struct mckernel_procfs_buffer *pbuf)
{
	return virt_to_phys(pbuf);
}

static void buf_free(unsigned long phys)
{
	procfs_buf_release_result(phys, procfs_buf_phys_to_virt_bridge,
			procfs_buf_free_page_bridge);
}

static unsigned long procfs_thread_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

static int procfs_thread_send_bridge(void *channel,
		struct ikc_scd_packet *packet)
{
	return ihk_ikc_send((struct ihk_ikc_channel_desc *)channel, packet, 0);
}

static void procfs_thread_pause_bridge(void)
{
	cpu_pause();
}

static void procfs_buf_free_top_bridge(struct mckernel_procfs_buffer *top)
{
	buf_free(virt_to_phys(top));
}

static void *procfs_buf_copy_bridge(void *dst, const void *src, size_t len)
{
	return memcpy(dst, src, len);
}

static int procfs_mem_page_fault_bridge(void *vm, unsigned long offset,
		unsigned long reason)
{
	return page_fault_process_vm((struct process_vm *)vm, (void *)offset,
			reason);
}

static int procfs_mem_virt_to_phys_bridge(void *page_table,
		unsigned long offset, unsigned long *physp)
{
	return ihk_mc_pt_virt_to_phys((struct page_table *)page_table,
			(void *)offset, physp);
}

static int procfs_mem_is_memory_bridge(unsigned long start, unsigned long end)
{
	return is_mckernel_memory(start, end);
}

static void *procfs_mem_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

static unsigned long procfs_pagemap_value_bridge(void *page_table,
		unsigned long addr)
{
	return ihk_mc_pt_virt_to_pagemap((struct page_table *)page_table, addr);
}

static unsigned long procfs_range_ulong_bridge(void *range, int field)
{
	struct vm_range *r = range;

	if (!r)
		return 0;
	switch (field) {
	case PROCFS_RANGE_FIELD_START:
		return r->start;
	case PROCFS_RANGE_FIELD_END:
		return r->end;
	case PROCFS_RANGE_FIELD_FLAG:
		return r->flag;
	default:
		return 0;
	}
}

static const char *procfs_range_path_bridge(void *range)
{
	struct vm_range *r = range;

	return r && r->memobj && r->memobj->path ? r->memobj->path : NULL;
}

static void *procfs_range_next_bridge(void *vm, void *range)
{
	return next_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range);
}

static void *procfs_backlog_alloc_bridge(unsigned long size,
					 unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void procfs_backlog_copy_bridge(void *dst, struct ikc_scd_packet *src,
				       unsigned long size)
{
	memcpy(dst, src, size);
}

static int procfs_backlog_add_bridge(procfs_backlog_fn_t backlog_fn,
				     void *arg)
{
	return add_backlog(backlog_fn, arg);
}

static void procfs_backlog_free_bridge(void *arg)
{
	kfree_tracked(arg, __FILE__, __LINE__);
}

static int buf_add(struct mckernel_procfs_buffer **top,
		   struct mckernel_procfs_buffer **cur,
		   const void *buf, int l)
{
	return procfs_buf_add_result(top, cur, buf, l, buf_alloc,
			procfs_buf_free_top_bridge, procfs_buf_copy_bridge);
}

static void
procfs_thread_ctl(struct thread *thread, int msg)
{
	struct ihk_ikc_channel_desc *syscall_channel;
	struct ikc_scd_packet packet;
	int done = 0;

	syscall_channel = get_this_cpu_local_var()->ikc2linux;
	procfs_thread_ctl_result(syscall_channel, &packet, &done, msg,
			ihk_mc_get_osnum(), thread->cpu_id, thread->proc->pid,
			thread->tid, procfs_thread_phys_bridge,
			procfs_thread_send_bridge, procfs_thread_pause_bridge);
}

void
procfs_create_thread(struct thread *thread)
{
	procfs_thread_ctl(thread, SCD_MSG_PROCFS_TID_CREATE);
}

void
procfs_delete_thread(struct thread *thread)
{
	procfs_thread_ctl(thread, SCD_MSG_PROCFS_TID_DELETE);
}

static int procfs_backlog(struct process_vm *vm, struct ikc_scd_packet *rpacket)
{
	(void)vm;

	return procfs_backlog_result(rpacket, do_procfs_backlog,
			procfs_backlog_alloc_bridge,
			procfs_backlog_copy_bridge,
			procfs_backlog_add_bridge,
			procfs_backlog_free_bridge,
			sizeof(struct ikc_scd_packet), IHK_MC_AP_NOWAIT);
}

/**
 * \brief The callback function for mckernel procfs files.
 *
 * \param rarg returned argument
 */
static int _process_procfs_request(struct ikc_scd_packet *rpacket, int *result)
{
	unsigned long rarg = rpacket->arg;
	unsigned long parg, pbuf;
	struct thread *thread = NULL;
	struct process *proc = NULL;
	struct process_vm *vm = NULL;
	struct procfs_read *r;
	int osnum = ihk_mc_get_osnum();
	int rosnum, ret, pid, tid, ans = -EIO, eof = 0;
	char *buf, *p = NULL;
	char *vbuf = NULL;
	char *tmp = NULL;
	struct mcs_rwlock_node_irqsave lock;
	unsigned long offset;
	int count;
	int npages;
	int readwrite = 0;
	int err = -EIO;
	struct mckernel_procfs_buffer *buf_top = NULL;
	struct mckernel_procfs_buffer *buf_cur = NULL;

	dprintf("process_procfs_request: invoked.\n");

	dprintf("rarg: %x\n", rarg);
	parg = ihk_mc_map_memory(NULL, rarg, sizeof(struct procfs_read));
	dprintf("parg: %x\n", parg);
	r = ihk_mc_map_virtual(parg, 1, PTATTR_WRITABLE | PTATTR_ACTIVE);
	if (r == NULL) {
		ihk_mc_unmap_memory(NULL, parg, sizeof(struct procfs_read));
		kprintf("ERROR: process_procfs_request: got a null procfs_read structure.\n");
		goto err;
	}
	dprintf("r: %p\n", r);

	if (procfs_is_release_result(rpacket->msg)) {
		err = procfs_release_request_result(r,
				procfs_buf_phys_to_virt_bridge,
				procfs_buf_free_page_bridge);
		goto err;
	}

	if (procfs_pbuf_is_empty_result(r->pbuf)) {
		tmp = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
		if (!tmp)
			goto err;
		buf = tmp;
		count = procfs_default_count_result();
	}
	else {
		dprintf("remote pbuf: %x\n", r->pbuf);
		pbuf = ihk_mc_map_memory(NULL, r->pbuf, r->count);
		dprintf("pbuf: %x\n", pbuf);
		count = procfs_remote_count_result(pbuf, r->count);
		npages = procfs_remote_npages_result(count);
		vbuf = ihk_mc_map_virtual(pbuf, npages,
					  PTATTR_WRITABLE|PTATTR_ACTIVE);
		dprintf("buf: %p\n", vbuf);
		if (vbuf == NULL) {
			ihk_mc_unmap_memory(NULL, pbuf, r->count);
			kprintf("ERROR: %s: got a null buffer.\n", __func__);
			goto err;
		}
		buf = vbuf;
		readwrite = r->readwrite;
		count = r->count;
		dprintf("fname: %s, offset: %lx, count:%d.\n", r->fname,
			r->offset, r->count);
	}
	offset = r->offset;

	/*
	 * check for "mcos%d/"
	 */
	ret = sscanf(r->fname, "mcos%d/", &rosnum);
	if (procfs_root_matched_result(ret)) {
		if (!procfs_osnum_match_result(osnum, rosnum)) {
			kprintf("ERROR: process_procfs_request osnum mismatch "
				"(we are %d != requested %d)\n",
				osnum, rosnum);
			goto end;
		}
		dprintf("matched mcos%d.\n", osnum);
	} else {
		goto end;
	}
	p = strchr(r->fname, '/') + 1;

	/* Processing for pattern "mcos%d/xxx" files should be here.
	   Its template is something like what follows:

	   if (pattern matches) {
	   	   get the data (at 'r->offset')
		   and write it to 'buf'
		   up to 'r->count' bytes.
		ans = written bytes;
		goto end;
	   }
	*/

	/*
	 * check for "mcos%d/PID/"
	 */
	ret = sscanf(p, "%d/", &pid);
	if (ret == 1) {
		struct mcs_rwlock_node_irqsave tlock;
		int tids;
		struct thread *thread1 = NULL;

		proc = find_process(pid, &lock);
		if(proc == NULL){
			kprintf("process_procfs_request: no such pid %d\n", pid);
			goto end;
		}
		p = strchr(p, '/') + 1;
		tid = pid;
		if((tids = sscanf(p, "task/%d/", &tid)) == 1){
			p = strchr(p, '/') + 1;
			p = strchr(p, '/') + 1;
		}
		tid = procfs_thread_tid_result(tids, tid, pid);

		mcs_rwlock_reader_lock(&proc->threads_lock, &tlock);
		for (thread = ((typeof(*thread) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread), siblings_list))); &thread->siblings_list != (&proc->threads_list); thread = ((typeof(*thread) *)((char *)(thread->siblings_list.next) - offsetof(typeof(*thread), siblings_list)))){
			if(thread->tid == tid)
				break;
			if(!thread1)
				thread1 = thread;
		}
		if(thread == NULL){
			kprintf("process_procfs_request: no such tid %d-%d\n", pid, tid);
			if(procfs_task_missing_terminal_result(tids)){
				mcs_rwlock_reader_unlock(&proc->threads_lock, &tlock);
				process_unlock(proc, &lock);
				goto end;
			}
			thread = thread1;
		}
		if(thread)
			hold_thread(thread);
		mcs_rwlock_reader_unlock(&proc->threads_lock, &tlock);
		hold_process(proc);
		vm = proc->vm;
		if(procfs_pointer_present_result((uintptr_t)vm))
			hold_process_vm(vm);
		process_unlock(proc, &lock);
	}
	else switch (procfs_entry_kind_result(p)) {
	case PROCFS_ENTRY_MCKERNEL:
		ret = procfs_root_entry_body_result(PROCFS_ENTRY_MCKERNEL,
				MCKERNEL_VERSION, BUILDID, 0, count,
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	case PROCFS_ENTRY_STAT: {	/* "/proc/stat" */
		extern int num_processors;	/* kernel/ap.c */

		ret = procfs_root_entry_body_result(PROCFS_ENTRY_STAT,
				NULL, NULL, num_processors, count,
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	}
#ifdef POSTK_DEBUG_ARCH_DEP_42 /* /proc/cpuinfo support added. */
	case PROCFS_ENTRY_CPUINFO: { /* "/proc/cpuinfo" */
		ans = ihk_mc_show_cpuinfo(buf, count, 0, &eof);
		if (procfs_format_error_result(ans, count))
			goto err;
		if (buf_add(&buf_top, &buf_cur, buf, ans) < 0)
			goto err;
		ans = 0;
		goto end;
	}
#endif /* POSTK_DEBUG_ARCH_DEP_42 */
	default:
		kprintf("unsupported procfs entry: %s\n", p);
		goto end;
	}

	/* 
	 * mcos%d/PID/mem
	 *
	 * The offset is treated as the beginning of the virtual address area
	 * of the process. The count is the length of the area.
	 */
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_MEM) {
		struct page_table *pt = vm->address_space->page_table;

#if 0
		if(!(proc->ptrace & PT_TRACED) ||
		   !(proc->status & (PS_STOPPED | PS_TRACED))){
			ans = -EIO;
			goto end;
		}
#endif

		ans = procfs_mem_copy_body_result(vm, pt, buf, r->offset,
				(unsigned long)r->count, readwrite,
				procfs_mem_page_fault_bridge,
				procfs_mem_virt_to_phys_bridge,
				procfs_mem_is_memory_bridge,
				procfs_mem_phys_to_virt_bridge,
				procfs_buf_copy_bridge);
		goto end;
	}

	/*
	 * mcos%d/PID/maps
	 */
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_MAPS) {
		struct vm_range *range;

		if (!ihk_rwspinlock_read_trylock_noirq(&vm->memory_range_lock)) {
			if (procfs_lock_failed_action_result((uintptr_t)result) ==
			    PROCFS_LOCK_ACTION_BACKLOG) {
				if ((err = procfs_backlog(vm, rpacket))) {
					goto err;
				}
			}
			else {
				*result = procfs_lock_retry_result();
			}
			goto out;
		}

		range = lookup_process_memory_range(vm, 0, -1);
		ans = procfs_maps_body_result(vm, range,
				(unsigned long)vm->vdso_addr,
				(unsigned long)vm->vvar_addr,
				vm->region.brk_start,
				vm->region.brk_end_allocated, count, &buf_top,
				&buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge, procfs_range_ulong_bridge,
				procfs_range_path_bridge,
				procfs_range_next_bridge);
		if (ans < 0) {
			ihk_rwspinlock_read_unlock_noirq(
					&vm->memory_range_lock);
			goto err;
		}

		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

		ans = 0;
		goto end;
	}
	
	/*
	 * mcos%d/PID/pagemap
	 */
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_PAGEMAP) {
		uint64_t *_buf = (uint64_t *)buf;
		unsigned long start, end;
		struct page_table *pt = proc->vm->address_space->page_table;

		ans = procfs_pagemap_range_result(offset, count, &start, &end);
		if (ans) {
			goto end;
		}

		if (!ihk_rwspinlock_read_trylock_noirq(&vm->memory_range_lock)) {
			if (procfs_lock_failed_action_result((uintptr_t)result) ==
			    PROCFS_LOCK_ACTION_BACKLOG) {
				if ((err = procfs_backlog(vm, rpacket))) {
					goto err;
				}
			}
			else {
				*result = procfs_lock_retry_result();
			}
			goto out;
		}

		ans = procfs_pagemap_body_result(pt, (unsigned long *)_buf,
				start, end, count, procfs_pagemap_value_bridge);
		if (ans < 0) {
			ihk_rwspinlock_read_unlock_noirq(
					&vm->memory_range_lock);
			goto err;
		}
		start = end;

		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

		dprintf("/proc/pagemap: 0x%lx - 0x%lx, count: %d\n",
			start, end, count);

		goto end;
	}

	/*
	 * mcos%d/PID/status
	 */
#define BITMASKS_BUF_SIZE	2048
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_STATUS) {
		extern int num_processors;	/* kernel/ap.c */
		struct vm_range *range;
		unsigned long lockedsize = 0;
		char *bitmasks;
		int bitmasks_offset = 0;
		char *cpu_bitmask, *cpu_list, *numa_bitmask, *numa_list;
		struct mcs_rwlock_node_irqsave lock;
		struct thread *thread_iter;
		int nr_threads = 0;
		struct procfs_status_body_input status_input;

		bitmasks = kmalloc_tracked(BITMASKS_BUF_SIZE, IHK_MC_AP_CRITICAL, __FILE__, __LINE__);
		if (!bitmasks) {
			kprintf("%s: error allocating /proc/self/status bitmaks buffer\n",
				__FUNCTION__);
			goto err;
		}

		if (!ihk_rwspinlock_read_trylock_noirq(&vm->memory_range_lock)) {
			if (procfs_lock_failed_action_result((uintptr_t)result) ==
			    PROCFS_LOCK_ACTION_BACKLOG) {
				if ((err = procfs_backlog(vm, rpacket))) {
					kfree_tracked(bitmasks, __FILE__, __LINE__);
					goto err;
				}
			}
			else {
				*result = procfs_lock_retry_result();
			}
			kfree_tracked(bitmasks, __FILE__, __LINE__);
			goto out;
		}
		range = lookup_process_memory_range(vm, 0, -1);
		lockedsize = procfs_locked_size_body_result(vm, range,
				procfs_range_ulong_bridge,
				procfs_range_next_bridge);
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

		cpu_bitmask = &bitmasks[bitmasks_offset];
		bitmasks_offset = procfs_bitmask_next_offset_result(
				bitmasks_offset, bitmap_scnprintf(cpu_bitmask,
				BITMASKS_BUF_SIZE - bitmasks_offset,
				thread->cpu_set.__bits, num_processors));

		cpu_list = &bitmasks[bitmasks_offset];
		bitmasks_offset = procfs_bitmask_next_offset_result(
				bitmasks_offset, bitmap_scnlistprintf(cpu_list,
				BITMASKS_BUF_SIZE - bitmasks_offset,
				thread->cpu_set.__bits, __CPU_SETSIZE));

		numa_bitmask = &bitmasks[bitmasks_offset];
		bitmasks_offset = procfs_bitmask_next_offset_result(
				bitmasks_offset, bitmap_scnprintf(numa_bitmask,
				BITMASKS_BUF_SIZE - bitmasks_offset,
				proc->vm->numa_mask, PROCESS_NUMA_MASK_BITS));

		numa_list = &bitmasks[bitmasks_offset];
		bitmasks_offset = procfs_bitmask_next_offset_result(
				bitmasks_offset, bitmap_scnlistprintf(numa_list,
				BITMASKS_BUF_SIZE - bitmasks_offset,
				proc->vm->numa_mask, PROCESS_NUMA_MASK_BITS));

		mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
			++nr_threads;
		}
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);

		status_input.pid = proc->pid;
		status_input.ruid = proc->ruid;
		status_input.euid = proc->euid;
		status_input.suid = proc->suid;
		status_input.fsuid = proc->fsuid;
		status_input.rgid = proc->rgid;
		status_input.egid = proc->egid;
		status_input.sgid = proc->sgid;
		status_input.fsgid = proc->fsgid;
		status_input.status = proc->status;
		status_input.nr_threads = nr_threads;
		status_input.lockedsize = lockedsize;
		status_input.cpu_bitmask = cpu_bitmask;
		status_input.cpu_list = cpu_list;
		status_input.numa_bitmask = numa_bitmask;
		status_input.numa_list = numa_list;
		ret = procfs_status_body_result(&status_input, count,
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0) {
			kfree_tracked(bitmasks, __FILE__, __LINE__);
			goto err;
		}
		kfree_tracked(bitmasks, __FILE__, __LINE__);
		ans = 0;
		goto end;
	}

	/* 
	 * mcos%d/PID/auxv
	 */
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_AUXV) {
		ret = procfs_pid_simple_entry_body_result(PROCFS_ENTRY_AUXV,
				proc->saved_auxv, proc->saved_cmdline,
				proc->saved_cmdline_len, "exe",
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	}

	/* 
	 * mcos%d/PID/cmdline
	 */
	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_CMDLINE) {
		ret = procfs_pid_simple_entry_body_result(PROCFS_ENTRY_CMDLINE,
				proc->saved_auxv, proc->saved_cmdline,
				proc->saved_cmdline_len, "exe",
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	}

	/* 
	 * mcos%d/PID/taks/PID/mem
	 *
	 * The offset is treated as the beginning of the virtual address area
	 * of the process. The count is the length of the area.
	 */

	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_COMM) {
		ret = procfs_pid_simple_entry_body_result(PROCFS_ENTRY_COMM,
				proc->saved_auxv, proc->saved_cmdline,
				proc->saved_cmdline_len, "exe",
				&buf_top, &buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	}

	if (procfs_entry_kind_result(p) == PROCFS_ENTRY_STAT) {
		const char *comm;
		char state;
		struct mcs_rwlock_node_irqsave lock;
		struct thread *thread_iter;
		int nr_threads = 0;
		struct procfs_stat_body_input stat_input;
		uintptr_t basename = procfs_comm_basename_result(
			(uintptr_t)proc->saved_cmdline);

		comm = (const char *)procfs_comm_name_result(
			(uintptr_t)"exe", basename);

		state = procfs_thread_stat_state_result(thread->status,
				thread->in_syscall_offload);

		mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
			++nr_threads;
		}
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);

		stat_input.tid = thread->tid;
		stat_input.comm = comm;
		stat_input.state = state;
		stat_input.ppid = thread->proc->ppid_parent->pid;
		stat_input.pid = thread->proc->pid;
		stat_input.nr_threads = nr_threads;
		stat_input.cpu_id = thread->cpu_id;
		ret = procfs_stat_body_result(&stat_input, count, &buf_top,
				&buf_cur, buf_alloc,
				procfs_buf_free_top_bridge,
				procfs_buf_copy_bridge);
		if (ret < 0)
			goto err;
		ans = 0;
		goto end;
	}

	if(thread)
		kprintf("unsupported procfs entry: %d/task/%d/%s\n", pid, tid, p);
	else
		kprintf("unsupported procfs entry: %d/%s\n", pid, p);

end:
	dprintf("ret: %d, eof: %d\n", ans, eof);
	err = procfs_finish_request_result(r, ans, eof, buf_top,
			procfs_buf_phys_bridge);
err:
	send_procfs_answer(rpacket, err);

out:
	if (vbuf) {
		ihk_mc_unmap_virtual(vbuf, npages);
		ihk_mc_unmap_memory(NULL, pbuf, r->count);
	}
	if (r) {
		ihk_mc_unmap_virtual(r, 1);
		ihk_mc_unmap_memory(NULL, parg, sizeof(struct procfs_read));
	}
	if (tmp) {
		_ihk_mc_free_pages(tmp, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}

	if(proc)
		release_process(proc);
	if(thread)
		release_thread(thread);
	if(vm)
		release_process_vm(vm);

	return err;
}

int process_procfs_request(struct ikc_scd_packet *rpacket)
{
	return _process_procfs_request(rpacket, NULL);
}

static int do_procfs_backlog(void *arg)
{
	struct ikc_scd_packet *rpacket = arg;
	int result = 0;

	_process_procfs_request(rpacket, &result);
	if (!result) {
		kfree_tracked(arg, __FILE__, __LINE__);
	}
	return result;
}
