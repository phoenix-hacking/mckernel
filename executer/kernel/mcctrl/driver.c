/* driver.c COPYRIGHT FUJITSU LIMITED 2016 */
/**
 * \file executer/kernel/driver.c
 *  License details are found in the file LICENSE.
 * \brief
 *  kernel module entry
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 *      Copyright (C) 2012  RIKEN AICS
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 *      Copyright (C) 2012 - 2013 Hitachi, Ltd.
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 *      Copyright (C) 2012 - 2013 Hitachi, Ltd.
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2013  The University of Tokyo
 */
/*
 * HISTORY:
 *  2013/09/02 shirasawa add terminate thread
 *  2013/08/19 shirasawa mcexec forward signal to MIC process
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/binfmts.h>
#include <linux/elf.h>
#include <linux/file.h>
#include <linux/err.h>
#include <linux/fs.h>
#include <linux/miscdevice.h>
#include <linux/slab.h>
#include <linux/device.h>
#include <linux/delay.h>
#include <linux/kallsyms.h>
#include <linux/version.h>
#include <linux/mm.h>
#include <linux/uaccess.h>
#include <linux/highmem.h>
#if defined(__has_include)
# if __has_include(<linux/rhelversion.h>)
#  include <linux/rhelversion.h>
# endif
#endif
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 8, 0)
#include <linux/mmap_lock.h>
#endif
#include <asm/msr.h>
#include <asm/vsyscall.h>
#include <asm/vgtod.h>
#include "mcctrl.h"
#include <mcctrl_rust.h>
#include <ihk/ihk_host_user.h>

#define OS_MAX_MINOR 64

#if defined(RHEL_RELEASE_CODE) && defined(RHEL_RELEASE_VERSION)
#define MCCTRL_RHEL_RELEASE_AT_LEAST(major, minor) \
	(RHEL_RELEASE_CODE >= RHEL_RELEASE_VERSION(major, minor))
#else
#define MCCTRL_RHEL_RELEASE_AT_LEAST(major, minor) 0
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 3, 0) && \
	!MCCTRL_RHEL_RELEASE_AT_LEAST(8, 10)
#define MCCTRL_VGTOD_VIRT ((void *)&VVAR(vsyscall_gtod_data))
#else
#define MCCTRL_VGTOD_VIRT NULL
#endif

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 8, 0)
#define MCCTRL_MMAP_WRITE_LOCK(mm) mmap_write_lock(mm)
#define MCCTRL_MMAP_WRITE_UNLOCK(mm) mmap_write_unlock(mm)
#else
#define MCCTRL_MMAP_WRITE_LOCK(mm) down_write(&(mm)->mmap_sem)
#define MCCTRL_MMAP_WRITE_UNLOCK(mm) up_write(&(mm)->mmap_sem)
#endif

#if !defined(MCCTRL_RUST_HELPERS) && KERNEL_VERSION(4, 11, 0) > LINUX_VERSION_CODE
void refcount_set(refcount_t *r, unsigned int n)
{
	atomic_set(&r->refs, n);
}

unsigned int refcount_read(const refcount_t *r)
{
	return atomic_read(&r->refs);
}

bool refcount_add_not_zero(unsigned int i, refcount_t *r)
{
	return atomic_add_unless(&r->refs, i, 0);
}

void refcount_add(unsigned int i, refcount_t *r)
{
	atomic_add(i, &r->refs);
}

bool refcount_inc_not_zero(refcount_t *r)
{
	return atomic_add_unless(&r->refs, 1, 0);
}

void refcount_inc(refcount_t *r)
{
	atomic_inc(&r->refs);
}

bool refcount_sub_and_test(unsigned int i, refcount_t *r)
{
	return atomic_sub_and_test(i, &r->refs);
}

bool refcount_dec_and_test(refcount_t *r)
{
	return atomic_dec_and_test(&r->refs);
}

void refcount_dec(refcount_t *r)
{
	atomic_dec(&r->refs);
}
#endif

#ifdef MCCTRL_RUST_HELPERS
#define MCCTRL_IKC_INLINE_FREE_ADDRS 4

/*
 * Host IHK implements ihk_ikc_get_processor_id as a function-like macro, not
 * an exported symbol. Rust cannot expand that macro, so define its legacy link
 * name inside mcctrl. Parenthesizing the declarator prevents macro expansion;
 * the body deliberately retains the pinned host-side CPU mapping semantics.
 */
int (ihk_ikc_get_processor_id)(void)
{
	return ihk_ikc_get_processor_id();
}

int mcctrl_ikc_send_wait(ihk_os_t os, int cpu, struct ikc_scd_packet *pisp,
		long int timeout, struct mcctrl_wakeup_desc *desc,
		int *do_frees, int free_addrs_count, ...)
{
	void *inline_addrs[MCCTRL_IKC_INLINE_FREE_ADDRS];
	void **free_addrs = inline_addrs;
	va_list ap;
	int i;
	int ret;

	if (free_addrs_count < 0) {
		return -EINVAL;
	}
	if (free_addrs_count > MCCTRL_IKC_INLINE_FREE_ADDRS) {
		free_addrs = kmalloc_array(free_addrs_count, sizeof(*free_addrs),
				GFP_ATOMIC);
		if (!free_addrs) {
			return -ENOMEM;
		}
	}

	va_start(ap, free_addrs_count);
	for (i = 0; i < free_addrs_count; i++) {
		free_addrs[i] = va_arg(ap, void *);
	}
	va_end(ap);

	ret = mcctrl_ikc_send_wait_array(os, cpu, pisp, timeout, desc,
			do_frees, free_addrs_count, free_addrs);

	if (free_addrs != inline_addrs) {
		kfree(free_addrs);
	}
	return ret;
}

void *mcctrl_ikc_kmalloc_atomic_bridge(size_t size)
{
	return kmalloc(size, GFP_ATOMIC);
}

void *mcctrl_ikc_kzalloc_atomic_bridge(size_t size)
{
	return kzalloc(size, GFP_ATOMIC);
}

void mcctrl_ikc_kfree_bridge(void *ptr)
{
	kfree(ptr);
}

size_t mcctrl_ikc_wakeup_desc_size_bridge(int free_addrs_count)
{
	return sizeof(struct mcctrl_wakeup_desc) +
		(free_addrs_count + 1) * sizeof(void *);
}

void mcctrl_ikc_desc_set_free_addr_bridge(struct mcctrl_wakeup_desc *desc,
		int index, void *addr)
{
	desc->free_addrs[index] = addr;
}

void mcctrl_ikc_desc_set_free_addrs_count_bridge(
		struct mcctrl_wakeup_desc *desc, int count)
{
	desc->free_addrs_count = count;
}

int mcctrl_ikc_desc_free_addrs_count_bridge(struct mcctrl_wakeup_desc *desc)
{
	return desc->free_addrs_count;
}

void *mcctrl_ikc_desc_free_addr_bridge(struct mcctrl_wakeup_desc *desc,
		int index)
{
	return desc->free_addrs[index];
}

void mcctrl_ikc_desc_set_free_at_put_bridge(struct mcctrl_wakeup_desc *desc,
		int free_at_put)
{
	desc->free_at_put = free_at_put;
}

int mcctrl_ikc_desc_free_at_put_bridge(struct mcctrl_wakeup_desc *desc)
{
	return desc->free_at_put;
}

void mcctrl_ikc_desc_init_waitqueue_bridge(struct mcctrl_wakeup_desc *desc)
{
	init_waitqueue_head(&desc->wq);
}

void mcctrl_ikc_desc_refcount_set_bridge(struct mcctrl_wakeup_desc *desc,
		unsigned int count)
{
	refcount_set(&desc->count, count);
}

int mcctrl_ikc_desc_refcount_dec_and_test_bridge(
		struct mcctrl_wakeup_desc *desc)
{
	return refcount_dec_and_test(&desc->count);
}

void mcctrl_ikc_desc_list_add_bridge(struct mcctrl_usrdata *usrdata,
		struct mcctrl_wakeup_desc *desc)
{
	unsigned long flags;

	spin_lock_irqsave(&usrdata->wakeup_descs_lock, flags);
	list_add(&desc->chain, &usrdata->wakeup_descs_list);
	spin_unlock_irqrestore(&usrdata->wakeup_descs_lock, flags);
}

void mcctrl_ikc_desc_list_del_bridge(struct mcctrl_usrdata *usrdata,
		struct mcctrl_wakeup_desc *desc)
{
	unsigned long flags;

	spin_lock_irqsave(&usrdata->wakeup_descs_lock, flags);
	list_del(&desc->chain);
	spin_unlock_irqrestore(&usrdata->wakeup_descs_lock, flags);
}

void mcctrl_ikc_desc_set_err_bridge(struct mcctrl_wakeup_desc *desc, int err)
{
	WRITE_ONCE(desc->err, err);
}

int mcctrl_ikc_desc_err_bridge(struct mcctrl_wakeup_desc *desc)
{
	return READ_ONCE(desc->err);
}

void mcctrl_ikc_desc_set_status_bridge(struct mcctrl_wakeup_desc *desc,
		int status)
{
	WRITE_ONCE(desc->status, status);
}

int mcctrl_ikc_desc_status_bridge(struct mcctrl_wakeup_desc *desc)
{
	return READ_ONCE(desc->status);
}

int mcctrl_ikc_desc_cmpxchg_status_bridge(struct mcctrl_wakeup_desc *desc,
		int old, int new)
{
	return cmpxchg(&desc->status, old, new);
}

void mcctrl_ikc_desc_wake_bridge(struct mcctrl_wakeup_desc *desc)
{
	wake_up_interruptible(&desc->wq);
}

int mcctrl_ikc_wait_interruptible_bridge(struct mcctrl_wakeup_desc *desc)
{
	return wait_event_interruptible(desc->wq, desc->status);
}

int mcctrl_ikc_wait_timeout_bridge(struct mcctrl_wakeup_desc *desc,
		long timeout)
{
	return wait_event_interruptible_timeout(desc->wq, desc->status,
			msecs_to_jiffies(timeout));
}

int mcctrl_ikc_wait_busy_bridge(struct mcctrl_wakeup_desc *desc,
		unsigned long timeout_msecs)
{
	unsigned long timeout_jiffies =
		jiffies + msecs_to_jiffies(timeout_msecs);

	while (time_before(jiffies, timeout_jiffies)) {
		schedule();
		if (READ_ONCE(desc->status)) {
			return 0;
		}
	}
	return -ETIME;
}

struct mcctrl_usrdata *mcctrl_ikc_alloc_usrdata_bridge(void)
{
	return kzalloc(sizeof(struct mcctrl_usrdata), GFP_ATOMIC);
}

void mcctrl_ikc_usrdata_set_info_bridge(struct mcctrl_usrdata *usrdata,
		ihk_os_t os, struct ihk_cpu_info *cpu_info,
		struct ihk_mem_info *mem_info)
{
	usrdata->os = os;
	usrdata->cpu_info = cpu_info;
	usrdata->mem_info = mem_info;
}

int mcctrl_ikc_cpu_info_n_cpus_bridge(struct ihk_cpu_info *cpu_info)
{
	return cpu_info ? cpu_info->n_cpus : 0;
}

int mcctrl_ikc_nr_cpu_ids_bridge(void)
{
	return nr_cpu_ids;
}

int mcctrl_ikc_alloc_channels_bridge(struct mcctrl_usrdata *usrdata,
		int num_channels)
{
	usrdata->num_channels = num_channels;
	usrdata->channels = kzalloc(sizeof(struct mcctrl_channel) *
			num_channels, GFP_ATOMIC);
	return usrdata->channels ? 0 : -ENOMEM;
}

int mcctrl_ikc_alloc_ikc2linux_bridge(struct mcctrl_usrdata *usrdata,
		int cpu_count)
{
	usrdata->ikc2linux = kzalloc(sizeof(struct ihk_ikc_channel_desc *) *
			cpu_count, GFP_ATOMIC);
	return usrdata->ikc2linux ? 0 : -ENOMEM;
}

void mcctrl_ikc_free_channels_bridge(struct mcctrl_usrdata *usrdata)
{
	kfree(usrdata->channels);
}

void mcctrl_ikc_free_ikc2linux_bridge(struct mcctrl_usrdata *usrdata)
{
	kfree(usrdata->ikc2linux);
}

void mcctrl_ikc_usrdata_init_sync_bridge(struct mcctrl_usrdata *usrdata)
{
	int i;

	init_waitqueue_head(&usrdata->wq_procfs);
	mutex_init(&usrdata->reserve_lock);
	mutex_init(&usrdata->part_exec_lock);

	for (i = 0; i < MCCTRL_PER_PROC_DATA_HASH_SIZE; ++i) {
		INIT_LIST_HEAD(&usrdata->per_proc_data_hash[i]);
		rwlock_init(&usrdata->per_proc_data_hash_lock[i]);
	}

	INIT_LIST_HEAD(&usrdata->cpu_topology_list);
	INIT_LIST_HEAD(&usrdata->node_topology_list);
	INIT_LIST_HEAD(&usrdata->part_exec_list);
	INIT_LIST_HEAD(&usrdata->wakeup_descs_list);
	spin_lock_init(&usrdata->wakeup_descs_lock);
}

int mcctrl_ikc_usrdata_num_channels_bridge(struct mcctrl_usrdata *usrdata)
{
	return usrdata->num_channels;
}

struct ihk_ikc_channel_desc *mcctrl_ikc_usrdata_channel_desc_bridge(
		struct mcctrl_usrdata *usrdata, int cpu)
{
	if (!usrdata || cpu < 0 || cpu >= usrdata->num_channels ||
	    !usrdata->channels) {
		return NULL;
	}
	return usrdata->channels[cpu].c;
}

void mcctrl_ikc_usrdata_set_channel_desc_bridge(
		struct mcctrl_usrdata *usrdata, int cpu,
		struct ihk_ikc_channel_desc *channel)
{
	usrdata->channels[cpu].c = channel;
}

struct ihk_ikc_channel_desc *mcctrl_ikc_usrdata_ikc2linux_desc_bridge(
		struct mcctrl_usrdata *usrdata, int cpu)
{
	if (!usrdata || cpu < 0 || cpu >= nr_cpu_ids || !usrdata->ikc2linux) {
		return NULL;
	}
	return usrdata->ikc2linux[cpu];
}

void mcctrl_ikc_usrdata_set_ikc2linux_desc_bridge(
		struct mcctrl_usrdata *usrdata, int cpu,
		struct ihk_ikc_channel_desc *channel)
{
	usrdata->ikc2linux[cpu] = channel;
}

int mcctrl_ikc_channel_port_bridge(struct ihk_ikc_channel_desc *channel)
{
	return channel->port;
}

ihk_os_t mcctrl_ikc_channel_remote_os_bridge(
		struct ihk_ikc_channel_desc *channel)
{
	return channel->remote_os;
}

int mcctrl_ikc_channel_send_write_cpu_bridge(
		struct ihk_ikc_channel_desc *channel)
{
	return channel->send.queue->write_cpu;
}

int mcctrl_ikc_channel_send_read_cpu_bridge(
		struct ihk_ikc_channel_desc *channel)
{
	return channel->send.queue->read_cpu;
}

struct ihk_ikc_channel_desc *mcctrl_ikc_info_channel_bridge(
		struct ihk_ikc_channel_info *param)
{
	return param->channel;
}

void mcctrl_ikc_info_set_packet_handler_bridge(
		struct ihk_ikc_channel_info *param, ihk_ikc_ph_t handler)
{
	param->packet_handler = handler;
}

void mcctrl_ikc_drain_wakeup_descs_bridge(struct mcctrl_usrdata *usrdata)
{
	unsigned long flags;
	struct mcctrl_wakeup_desc *mwd_entry, *mwd_next;
	int i;

	spin_lock_irqsave(&usrdata->wakeup_descs_lock, flags);
	list_for_each_entry_safe(mwd_entry, mwd_next,
				&usrdata->wakeup_descs_list, chain) {
		list_del(&mwd_entry->chain);

		for (i = 0; i < mwd_entry->free_addrs_count; i++) {
			kfree(mwd_entry->free_addrs[i]);
		}
	}
	spin_unlock_irqrestore(&usrdata->wakeup_descs_lock, flags);
}

void mcctrl_ikc_drain_part_exec_list_bridge(struct mcctrl_usrdata *usrdata)
{
	mutex_lock(&usrdata->part_exec_lock);
	while (!list_empty(&usrdata->part_exec_list)) {
		struct mcctrl_part_exec *pe;

		pe = list_first_entry(&usrdata->part_exec_list,
				struct mcctrl_part_exec, chain);
		list_del(&pe->chain);
		kfree(pe);
	}
	mutex_unlock(&usrdata->part_exec_lock);
}

void mcctrl_ikc_log_usrdata_missing_bridge(const char *func)
{
	pr_err("%s: error: mcctrl_usrdata not found\n", func);
}

void mcctrl_ikc_log_os_missing_bridge(const char *func)
{
	pr_err("%s: error: os not found\n", func);
}

void mcctrl_ikc_log_warn_packet_bridge(const char *func)
{
	kprintf("%s: WARNING: packet received\n", func);
}

void mcctrl_ikc_log_invalid_linux_cpu_bridge(const char *func, int cpu)
{
	kprintf("%s: invalid Linux CPU id %d\n", func, cpu);
}

void mcctrl_ikc_log_invalid_source_cpu_bridge(int cpu)
{
	kprintf("Invalid connect source processor: %d\n", cpu);
}

void mcctrl_ikc_log_unknown_packet_bridge(struct ikc_scd_packet *packet)
{
	printk(KERN_ERR "mcctrl:syscall_packet_handler:"
			"unknown message (%d.%d.%d.%d.%d.%#lx)\n",
			packet->msg, packet->ref, packet->osnum, packet->pid,
			packet->err, packet->arg);
}

void mcctrl_ikc_log_alloc_usrdata_failed_bridge(const char *func)
{
	printk("%s: error: allocating mcctrl_usrdata\n", func);
}

void mcctrl_ikc_log_missing_cpu_mem_bridge(const char *func)
{
	printk("%s: cannot obtain OS CPU and memory information.\n", func);
}

void mcctrl_ikc_log_invalid_cpu_count_bridge(const char *func)
{
	printk("%s: Error: # of cpu is invalid.\n", func);
}

void mcctrl_ikc_log_alloc_channels_failed_bridge(void)
{
	printk("Error: cannot allocate channels.\n");
}

void mcctrl_ikc_log_alloc_ikc2linux_failed_bridge(void)
{
	printk("Error: cannot allocate ikc2linux channels.\n");
}

void mcctrl_ikc_log_no_channel_bridge(const char *func)
{
	kprintf("%s: error: no channel found?\n", func);
}

void mcctrl_ikc_log_send_failed_bridge(const char *func, int ret)
{
	pr_warn("%s: mcctrl_ikc_send failed: %d\n", func, ret);
}

void mcctrl_ikc_log_desc_alloc_failed_bridge(const char *func)
{
	pr_warn("%s: Could not allocate wakeup descriptor", func);
}

void *mcctrl_sysfs_get_usrdata_bridge(ihk_os_t os)
{
	return ihk_host_os_get_usrdata(os);
}

ihk_os_t mcctrl_sysfs_usrdata_os_bridge(struct mcctrl_usrdata *usrdata)
{
	return usrdata ? usrdata->os : NULL;
}

ihk_device_t mcctrl_sysfs_os_to_dev_bridge(ihk_os_t os)
{
	return ihk_os_to_dev(os);
}

void mcctrl_sysfs_warn_missing_usrdata_bridge(const char *func)
{
	pr_warn("%s: warning: mcctrl_usrdata not found\n", func);
}

void mcctrl_sysfs_log_error_bridge(const char *where, int error)
{
	pr_err("mcctrl:%s failed. %d\n", where, error);
}

void mcctrl_cpumap_clear_bridge(void *mask)
{
	cpumask_clear((cpumask_t *)mask);
}

int mcctrl_cpumap_test_cpu_bridge(int cpu, const void *mask)
{
	return cpumask_test_cpu(cpu, (const cpumask_t *)mask);
}

void mcctrl_cpumap_set_cpu_bridge(int cpu, void *mask)
{
	cpumask_set_cpu(cpu, (cpumask_t *)mask);
}

const int *mcctrl_usrdata_cpu_mapping_bridge(struct mcctrl_usrdata *udp)
{
	return udp && udp->cpu_info ? udp->cpu_info->mapping : NULL;
}

const int *mcctrl_usrdata_cpu_hw_ids_bridge(struct mcctrl_usrdata *udp)
{
	return udp && udp->cpu_info ? udp->cpu_info->hw_ids : NULL;
}

int mcctrl_usrdata_cpu_count_bridge(struct mcctrl_usrdata *udp)
{
	return udp && udp->cpu_info ? udp->cpu_info->n_cpus : 0;
}

const int *mcctrl_usrdata_numa_mapping_bridge(struct mcctrl_usrdata *udp)
{
	return udp && udp->mem_info ? udp->mem_info->numa_mapping : NULL;
}

int mcctrl_usrdata_numa_count_bridge(struct mcctrl_usrdata *udp)
{
	return udp && udp->mem_info ? udp->mem_info->n_numa_nodes : 0;
}

unsigned long *mcctrl_sysfs_cpu_online_bridge(struct mcctrl_usrdata *udp)
{
	return udp ? udp->cpu_online : NULL;
}

size_t mcctrl_sysfs_cpu_online_size_bridge(void)
{
	return sizeof(((struct mcctrl_usrdata *)0)->cpu_online);
}

int mcctrl_sysfs_cpu_longs_bridge(void)
{
	return CPU_LONGS;
}

int mcctrl_sysfs_bits_per_long_bridge(void)
{
	return BITS_PER_LONG;
}

int mcctrl_sysfs_nr_cpu_ids_bridge(void)
{
	return nr_cpu_ids;
}

int mcctrl_sysfs_max_numnodes_bridge(void)
{
	return MAX_NUMNODES;
}

void *mcctrl_sysfs_numa_online_bridge(struct mcctrl_usrdata *udp)
{
	return udp ? &udp->numa_online : NULL;
}

size_t mcctrl_sysfs_numa_online_size_bridge(void)
{
	return sizeof(((struct mcctrl_usrdata *)0)->numa_online);
}

void mcctrl_sysfs_node_set_bridge(int node, void *mask)
{
	node_set(node, *(nodemask_t *)mask);
}

void *mcctrl_sysfs_alloc_cache_topology_bridge(
		struct ihk_cache_topology *saved)
{
	struct cache_topology *cache = kmalloc(sizeof(*cache), GFP_KERNEL);

	if (cache) {
		cache->saved = saved;
	}
	return cache;
}

void *mcctrl_sysfs_alloc_cpu_topology_bridge(int index,
		struct ihk_cpu_topology *saved)
{
	struct mcctrl_cpu_topology *topology =
		kmalloc(sizeof(*topology), GFP_KERNEL);

	if (topology) {
		INIT_LIST_HEAD(&topology->cache_list);
		topology->mckernel_cpu_id = index;
		topology->saved = saved;
	}
	return topology;
}

void *mcctrl_sysfs_alloc_node_topology_bridge(
		struct ihk_node_topology *saved)
{
	struct node_topology *node = kmalloc(sizeof(*node), GFP_KERNEL);

	if (node) {
		node->saved = saved;
	}
	return node;
}

void mcctrl_sysfs_kfree_bridge(void *ptr)
{
	kfree(ptr);
}

struct ihk_cpu_topology *mcctrl_sysfs_get_cpu_topology_bridge(
		ihk_device_t dev, int hw_id)
{
	return ihk_device_get_cpu_topology(dev, hw_id);
}

struct ihk_node_topology *mcctrl_sysfs_get_node_topology_bridge(
		ihk_device_t dev, int node)
{
	return ihk_device_get_node_topology(dev, node);
}

void *mcctrl_sysfs_saved_cpu_core_siblings_bridge(
		struct ihk_cpu_topology *saved)
{
	return saved ? &saved->core_siblings : NULL;
}

void *mcctrl_sysfs_saved_cpu_thread_siblings_bridge(
		struct ihk_cpu_topology *saved)
{
	return saved ? &saved->thread_siblings : NULL;
}

void *mcctrl_sysfs_saved_cpu_first_cache_bridge(
		struct ihk_cpu_topology *saved)
{
	if (!saved || list_empty(&saved->cache_topology_list)) {
		return NULL;
	}
	return list_first_entry(&saved->cache_topology_list,
			struct ihk_cache_topology, chain);
}

void *mcctrl_sysfs_saved_cpu_next_cache_bridge(
		struct ihk_cpu_topology *saved, struct ihk_cache_topology *cache)
{
	struct list_head *next;

	if (!saved || !cache) {
		return NULL;
	}
	next = cache->chain.next;
	if (next == &saved->cache_topology_list) {
		return NULL;
	}
	return list_entry(next, struct ihk_cache_topology, chain);
}

void *mcctrl_sysfs_saved_cache_shared_cpu_map_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? &saved->shared_cpu_map : NULL;
}

int mcctrl_sysfs_saved_cache_index_bridge(struct ihk_cache_topology *saved)
{
	return saved ? saved->index : 0;
}

long *mcctrl_sysfs_saved_cache_level_bridge(struct ihk_cache_topology *saved)
{
	return saved ? &saved->level : NULL;
}

char *mcctrl_sysfs_saved_cache_type_bridge(struct ihk_cache_topology *saved)
{
	return saved ? saved->type : NULL;
}

char *mcctrl_sysfs_saved_cache_size_str_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? saved->size_str : NULL;
}

long *mcctrl_sysfs_saved_cache_coherency_line_size_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? &saved->coherency_line_size : NULL;
}

long *mcctrl_sysfs_saved_cache_number_of_sets_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? &saved->number_of_sets : NULL;
}

long *mcctrl_sysfs_saved_cache_physical_line_partition_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? &saved->physical_line_partition : NULL;
}

long *mcctrl_sysfs_saved_cache_ways_of_associativity_bridge(
		struct ihk_cache_topology *saved)
{
	return saved ? &saved->ways_of_associativity : NULL;
}

void *mcctrl_sysfs_cache_saved_bridge(struct cache_topology *cache)
{
	return cache ? cache->saved : NULL;
}

void *mcctrl_sysfs_cache_shared_cpu_map_bridge(struct cache_topology *cache)
{
	return cache ? &cache->shared_cpu_map : NULL;
}

void *mcctrl_sysfs_cpu_saved_bridge(struct mcctrl_cpu_topology *cpu)
{
	return cpu ? cpu->saved : NULL;
}

int mcctrl_sysfs_cpu_mckernel_id_bridge(struct mcctrl_cpu_topology *cpu)
{
	return cpu ? cpu->mckernel_cpu_id : -1;
}

void *mcctrl_sysfs_cpu_core_siblings_bridge(struct mcctrl_cpu_topology *cpu)
{
	return cpu ? &cpu->core_siblings : NULL;
}

void *mcctrl_sysfs_cpu_thread_siblings_bridge(struct mcctrl_cpu_topology *cpu)
{
	return cpu ? &cpu->thread_siblings : NULL;
}

long *mcctrl_sysfs_saved_cpu_physical_package_id_bridge(
		struct ihk_cpu_topology *saved)
{
	return saved ? &saved->physical_package_id : NULL;
}

long *mcctrl_sysfs_saved_cpu_core_id_bridge(struct ihk_cpu_topology *saved)
{
	return saved ? &saved->core_id : NULL;
}

void mcctrl_sysfs_add_cache_to_cpu_bridge(struct mcctrl_cpu_topology *cpu,
		struct cache_topology *cache)
{
	list_add(&cache->chain, &cpu->cache_list);
}

void mcctrl_sysfs_add_cpu_to_usrdata_bridge(struct mcctrl_usrdata *udp,
		struct mcctrl_cpu_topology *cpu)
{
	list_add(&cpu->chain, &udp->cpu_topology_list);
}

void *mcctrl_sysfs_first_cpu_topology_bridge(struct mcctrl_usrdata *udp)
{
	if (!udp || list_empty(&udp->cpu_topology_list)) {
		return NULL;
	}
	return list_first_entry(&udp->cpu_topology_list,
			struct mcctrl_cpu_topology, chain);
}

void *mcctrl_sysfs_next_cpu_topology_bridge(struct mcctrl_usrdata *udp,
		struct mcctrl_cpu_topology *cpu)
{
	struct list_head *next;

	if (!udp || !cpu) {
		return NULL;
	}
	next = cpu->chain.next;
	if (next == &udp->cpu_topology_list) {
		return NULL;
	}
	return list_entry(next, struct mcctrl_cpu_topology, chain);
}

void *mcctrl_sysfs_first_cpu_cache_bridge(struct mcctrl_cpu_topology *cpu)
{
	if (!cpu || list_empty(&cpu->cache_list)) {
		return NULL;
	}
	return list_first_entry(&cpu->cache_list, struct cache_topology, chain);
}

void *mcctrl_sysfs_next_cpu_cache_bridge(struct mcctrl_cpu_topology *cpu,
		struct cache_topology *cache)
{
	struct list_head *next;

	if (!cpu || !cache) {
		return NULL;
	}
	next = cache->chain.next;
	if (next == &cpu->cache_list) {
		return NULL;
	}
	return list_entry(next, struct cache_topology, chain);
}

void *mcctrl_sysfs_pop_cpu_cache_bridge(struct mcctrl_cpu_topology *cpu)
{
	struct cache_topology *cache;

	if (!cpu || list_empty(&cpu->cache_list)) {
		return NULL;
	}
	cache = list_first_entry(&cpu->cache_list, struct cache_topology,
			chain);
	list_del(&cache->chain);
	return cache;
}

void *mcctrl_sysfs_pop_cpu_topology_bridge(struct mcctrl_usrdata *udp)
{
	struct mcctrl_cpu_topology *cpu;

	if (!udp || list_empty(&udp->cpu_topology_list)) {
		return NULL;
	}
	cpu = list_first_entry(&udp->cpu_topology_list,
			struct mcctrl_cpu_topology, chain);
	list_del(&cpu->chain);
	return cpu;
}

void *mcctrl_sysfs_saved_node_cpumap_bridge(struct ihk_node_topology *saved)
{
	return saved ? &saved->cpumap : NULL;
}

void *mcctrl_sysfs_node_cpumap_bridge(struct node_topology *node)
{
	return node ? &node->cpumap : NULL;
}

void mcctrl_sysfs_node_set_mckernel_id_bridge(struct node_topology *node,
		int id)
{
	node->mckernel_numa_id = id;
}

int mcctrl_sysfs_node_mckernel_id_bridge(struct node_topology *node)
{
	return node ? node->mckernel_numa_id : -1;
}

char *mcctrl_sysfs_node_distance_string_bridge(struct node_topology *node)
{
	return node ? node->mckernel_numa_distance_s : NULL;
}

void mcctrl_sysfs_add_node_to_usrdata_bridge(struct mcctrl_usrdata *udp,
		struct node_topology *node)
{
	list_add(&node->chain, &udp->node_topology_list);
}

void *mcctrl_sysfs_first_node_topology_bridge(struct mcctrl_usrdata *udp)
{
	if (!udp || list_empty(&udp->node_topology_list)) {
		return NULL;
	}
	return list_first_entry(&udp->node_topology_list,
			struct node_topology, chain);
}

void *mcctrl_sysfs_next_node_topology_bridge(struct mcctrl_usrdata *udp,
		struct node_topology *node)
{
	struct list_head *next;

	if (!udp || !node) {
		return NULL;
	}
	next = node->chain.next;
	if (next == &udp->node_topology_list) {
		return NULL;
	}
	return list_entry(next, struct node_topology, chain);
}

void *mcctrl_sysfs_pop_node_topology_bridge(struct mcctrl_usrdata *udp)
{
	struct node_topology *node;

	if (!udp || list_empty(&udp->node_topology_list)) {
		return NULL;
	}
	node = list_first_entry(&udp->node_topology_list,
			struct node_topology, chain);
	list_del(&node->chain);
	return node;
}

int mcctrl_sysfs_node_distance_bridge(int from, int to)
{
	return node_distance(from, to);
}

int mcctrl_sysfs_cpu_to_node_bridge(int cpu)
{
	return cpu_to_node(cpu);
}
#endif

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 19, 0)
#define MCCTRL_COPY_STRING_KERNEL(arg, bprm) copy_string_kernel((arg), (bprm))
#else
#define MCCTRL_COPY_STRING_KERNEL(arg, bprm) copy_strings_kernel(1, &(arg), (bprm))
#endif

#if MCCTRL_RHEL_RELEASE_AT_LEAST(8, 10) && \
	LINUX_VERSION_CODE < KERNEL_VERSION(5, 19, 0)
/*
 * Rocky/RHEL 8.10 hides prepare_binprm() from external modules. The binfmt
 * handler has already entered exec's binfmt path, so after swapping
 * bprm->file to mcexec only the probe buffer needs refresh.
 */
static int mcctrl_prepare_binprm_for_binfmt(struct linux_binprm *bprm)
{
	loff_t pos = 0;

	memset(bprm->buf, 0, BINPRM_BUF_SIZE);
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 14, 0)
	return kernel_read(bprm->file, bprm->buf, BINPRM_BUF_SIZE, &pos);
#else
	return kernel_read(bprm->file, pos, bprm->buf, BINPRM_BUF_SIZE);
#endif
}
#define MCCTRL_PREPARE_BINPRM(bprm) mcctrl_prepare_binprm_for_binfmt(bprm)
#else
#define MCCTRL_PREPARE_BINPRM(bprm) prepare_binprm(bprm)
#endif

extern long __mcctrl_control(ihk_os_t, unsigned int, unsigned long,
                             struct file *);
extern int prepare_ikc_channels(ihk_os_t os);
extern void destroy_ikc_channels(ihk_os_t os);
#ifndef DO_USER_MODE
extern void mcctrl_syscall_init(void);
#endif
extern void procfs_init(int);
extern void procfs_exit(int);

extern void uti_attr_finalize(void);
extern void binfmt_mcexec_init(void);
extern void binfmt_mcexec_exit(void);
#ifdef ENABLE_TOFU
extern void mcctrl_file_to_pidfd_hash_init(void);
#endif

extern int mcctrl_os_read_cpu_register(ihk_os_t os, int cpu,
		struct ihk_os_cpu_register *desc);
extern int mcctrl_os_write_cpu_register(ihk_os_t os, int cpu,
		struct ihk_os_cpu_register *desc);
extern int mcctrl_get_request_os_cpu(ihk_os_t os, int *cpu);
unsigned long
reserve_user_space_common(struct mcctrl_usrdata *usrdata,
			  unsigned long start, unsigned long end);

#ifdef MCCTRL_RUST_HELPERS
extern int load_elf(struct linux_binprm *bprm);

static struct linux_binfmt mcexec_rust_format = {
	.module		= THIS_MODULE,
	.load_binary	= load_elf,
};
#endif

#ifdef ENABLE_TOFU
extern void mcctrl_tofu_hijack_release_handlers(void);
extern void mcctrl_tofu_restore_release_handlers(void);
#endif

#ifdef MCCTRL_RUST_HELPERS
static long mcctrl_driver_control_bridge(unsigned long os,
		unsigned int request, unsigned long arg, unsigned long file)
{
	return __mcctrl_control((ihk_os_t)os, request, arg,
			(struct file *)file);
}
#endif

static long mcctrl_ioctl(ihk_os_t os, unsigned int request, void *priv,
                         unsigned long arg, struct file *file)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)priv;
	return mcctrl_driver_ioctl_body_result((unsigned long)os, request,
			arg, (unsigned long)file, mcctrl_driver_control_bridge);
#else
	return __mcctrl_control(os, request, arg, file);
#endif
}

static struct ihk_os_user_call_handler mcctrl_uchs[] = {
	{ .request = MCEXEC_UP_PREPARE_IMAGE, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_TRANSFER, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_START_IMAGE, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_WAIT_SYSCALL, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_RET_SYSCALL, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_LOAD_SYSCALL, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_SEND_SIGNAL, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_CPU, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_NODES, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_CPUSET, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_CREATE_PPD, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_STRNCPY_FROM_USER, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_PREPARE_DMA, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_FREE_DMA, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_OPEN_EXEC, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_CLOSE_EXEC, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_CRED, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_CREDV, .func = mcctrl_ioctl },
#ifdef MCEXEC_BIND_MOUNT
	{ .request = MCEXEC_UP_SYS_MOUNT, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_SYS_UMOUNT, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_SYS_UNSHARE, .func = mcctrl_ioctl },
#endif // MCEXEC_BIND_MOUNT
	{ .request = MCEXEC_UP_UTI_GET_CTX, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_UTI_SWITCH_CTX, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_SIG_THREAD, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_SYSCALL_THREAD, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_TERMINATE_THREAD, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_GET_NUM_POOL_THREADS, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_UTI_ATTR, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_RELEASE_USER_SPACE, .func = mcctrl_ioctl },
	{ .request = MCEXEC_UP_DEBUG_LOG, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_NUM, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_SET, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_GET, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_ENABLE, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_DISABLE, .func = mcctrl_ioctl },
	{ .request = IHK_OS_AUX_PERF_DESTROY, .func = mcctrl_ioctl },
	{ .request = IHK_OS_GETRUSAGE, .func = mcctrl_ioctl },
};

static struct ihk_os_kernel_call_handler mcctrl_kernel_handlers = {
	.get_request_cpu = mcctrl_get_request_os_cpu,
	.read_cpu_register = mcctrl_os_read_cpu_register,
	.write_cpu_register = mcctrl_os_write_cpu_register,
};

static struct ihk_os_user_call mcctrl_uc_proto = {
	.num_handlers = sizeof(mcctrl_uchs) / sizeof(mcctrl_uchs[0]),
	.handlers = mcctrl_uchs,
};

static struct ihk_os_user_call mcctrl_uc[OS_MAX_MINOR];

static ihk_os_t os[OS_MAX_MINOR];

#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_driver_get_os_slot_bridge(int index)
{
	return os[index];
}

static void mcctrl_driver_set_os_slot_bridge(int index, void *value)
{
	os[index] = (ihk_os_t)value;
}
#endif

ihk_os_t osnum_to_os(int n)
{
#ifdef MCCTRL_RUST_HELPERS
	return (ihk_os_t)mcctrl_driver_osnum_to_os_body_result(
			n, mcctrl_driver_get_os_slot_bridge);
#else
	return os[n];
#endif
}

#ifdef MCCTRL_RUST_HELPERS
void mcctrl_preempt_disable_bridge(void)
{
	preempt_disable();
}

void mcctrl_preempt_enable_bridge(void)
{
	preempt_enable();
}

void *mcctrl_arch_kallsyms_lookup_bridge(const char *name)
{
	return (void *)kallsyms_lookup_name(name);
}

unsigned long mcctrl_arch_vdso_size_bridge(void *image)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 16, 0)
	return ((struct vdso_image *)image)->size;
#else
	return 0;
#endif
}

void *mcctrl_arch_vdso_data_bridge(void *image)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 16, 0)
	return ((struct vdso_image *)image)->data;
#else
	return NULL;
#endif
}

void *mcctrl_arch_vgtod_virt_bridge(void)
{
	return MCCTRL_VGTOD_VIRT;
}

unsigned long mcctrl_arch_virt_to_phys_bridge(void *ptr)
{
	return virt_to_phys(ptr);
}

void mcctrl_arch_wmb_bridge(void)
{
	wmb();
}

int mcctrl_arch_mutex_lock_reserve_bridge(struct mcctrl_usrdata *usrdata)
{
	return mutex_lock_killable(&usrdata->reserve_lock);
}

void mcctrl_arch_mutex_unlock_reserve_bridge(struct mcctrl_usrdata *usrdata)
{
	mutex_unlock(&usrdata->reserve_lock);
}

void mcctrl_arch_mmap_write_lock_bridge(void)
{
	MCCTRL_MMAP_WRITE_LOCK(current->mm);
}

void mcctrl_arch_mmap_write_unlock_bridge(void)
{
	MCCTRL_MMAP_WRITE_UNLOCK(current->mm);
}

unsigned long mcctrl_arch_first_vma_start_bridge(void)
{
	struct vm_area_struct *vma = find_vma(current->mm, 0);

	return vma ? vma->vm_start : 0;
}

unsigned long mcctrl_arch_reserve_user_space_common_bridge(
		struct mcctrl_usrdata *usrdata, unsigned long start,
		unsigned long end)
{
	return reserve_user_space_common(usrdata, start, end);
}

int mcctrl_arch_is_err_value_bridge(unsigned long value)
{
	return IS_ERR_VALUE(value);
}

void *mcctrl_arch_os_to_dev_bridge(ihk_os_t os)
{
	return ihk_os_to_dev(os);
}

unsigned long mcctrl_arch_device_map_memory_bridge(
		ihk_device_t dev, unsigned long phys, unsigned long size)
{
	return ihk_device_map_memory(dev, phys, size);
}

void *mcctrl_arch_device_map_virtual_bridge(
		ihk_device_t dev, unsigned long phys, unsigned long size)
{
	return ihk_device_map_virtual(dev, phys, size, NULL, 0);
}

void mcctrl_arch_device_unmap_virtual_bridge(
		ihk_device_t dev, void *virt, unsigned long size)
{
	ihk_device_unmap_virtual(dev, virt, size);
}

void mcctrl_arch_device_unmap_memory_bridge(
		ihk_device_t dev, unsigned long phys, unsigned long size)
{
	ihk_device_unmap_memory(dev, phys, size);
}

void *mcctrl_arch_get_user_sp_bridge(void)
{
	unsigned long usp;

	asm volatile("movq %%gs:0xaf80, %0" : "=r" (usp));
	return (void *)usp;
}

void mcctrl_arch_set_user_sp_bridge(void *usp)
{
	asm volatile("movq %0, %%gs:0xaf80" :: "r" (usp));
}

void mcctrl_arch_restore_tls_bridge(unsigned long addr)
{
	wrmsrl(MSR_FS_BASE, addr);
}

int mcctrl_arch_copy_from_user_bridge(void *dst, const void __user *src,
				      unsigned long size)
{
	return copy_from_user(dst, src, size);
}

unsigned long mcctrl_arch_read_fs_base_bridge(void)
{
	unsigned long fs_base;

	rdmsrl(MSR_FS_BASE, fs_base);
	return fs_base;
}

void mcctrl_arch_pr_err_copy_from_user_bridge(const char *func)
{
	pr_err("%s: copy_from_user failed.\n", func);
}

void mcctrl_binfmt_insert_bridge(void)
{
	insert_binfmt(&mcexec_rust_format);
}

void mcctrl_binfmt_unregister_bridge(void)
{
	unregister_binfmt(&mcexec_rust_format);
}

int mcctrl_binfmt_os_alive_bridge(void)
{
	return mcctrl_os_alive();
}

int mcctrl_binfmt_envc_bridge(struct linux_binprm *bprm)
{
	return bprm->envc;
}

int mcctrl_binfmt_argc_bridge(struct linux_binprm *bprm)
{
	return bprm->argc;
}

void mcctrl_binfmt_inc_argc_bridge(struct linux_binprm *bprm)
{
	bprm->argc++;
}

unsigned long mcctrl_binfmt_p_bridge(struct linux_binprm *bprm)
{
	return bprm->p;
}

void *mcctrl_binfmt_buf_bridge(struct linux_binprm *bprm)
{
	return bprm->buf;
}

void *mcctrl_binfmt_alloc_atomic_bridge(unsigned long size)
{
	return kmalloc(size, GFP_ATOMIC);
}

void *mcctrl_binfmt_alloc_kernel_bridge(unsigned long size)
{
	return kmalloc(size, GFP_KERNEL);
}

void mcctrl_binfmt_free_bridge(void *ptr)
{
	kfree(ptr);
}

void mcctrl_binfmt_pr_alloc_pbuf_bridge(void)
{
	printk("%s: error: allocating pbuf\n", "load_elf");
}

const char *mcctrl_binfmt_path_bridge(struct linux_binprm *bprm,
				      char *pbuf, unsigned long size)
{
	const char *path = d_path(&bprm->file->f_path, pbuf, size);

	if (!path || IS_ERR(path))
		path = bprm->interp;
	return path;
}

int mcctrl_binfmt_get_user_arg_page_bridge(struct linux_binprm *bprm,
					   void **page_out)
{
	struct page *page;
	int rc;

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 5, 0)
	rc = get_user_pages_remote(bprm->mm, bprm->p, 1,
			FOLL_FORCE, &page, NULL);
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(4,10,0)
	rc = get_user_pages_remote(current, bprm->mm, bprm->p, 1,
			FOLL_FORCE, &page, NULL, NULL);
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(4,9,0)
	rc = get_user_pages_remote(current, bprm->mm, bprm->p, 1,
			FOLL_FORCE, &page, NULL);
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(4,6,0)
	rc = get_user_pages_remote(current, bprm->mm, bprm->p, 1, 0, 1,
			&page, NULL);
#else
	rc = get_user_pages(current, bprm->mm, bprm->p, 1, 0, 1,
			&page, NULL);
#endif
	if (rc > 0)
		*page_out = page;
	return rc;
}

void *mcctrl_binfmt_kmap_atomic_bridge(void *page)
{
	return kmap_atomic((struct page *)page
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,4,0)
			, KM_USER0
#endif
			);
}

void mcctrl_binfmt_kunmap_atomic_bridge(void *addr)
{
	kunmap_atomic(addr
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,4,0)
			, KM_USER0
#endif
			);
}

void mcctrl_binfmt_put_page_bridge(void *page)
{
	put_page((struct page *)page);
}

void *mcctrl_binfmt_open_exec_bridge(void)
{
	return open_exec(MCEXEC_PATH);
}

int mcctrl_binfmt_ptr_is_err_bridge(const void *ptr)
{
	return IS_ERR(ptr);
}

void mcctrl_binfmt_fput_bridge(void *file)
{
	fput((struct file *)file);
}

int mcctrl_binfmt_remove_arg_zero_bridge(struct linux_binprm *bprm)
{
	return remove_arg_zero(bprm);
}

int mcctrl_binfmt_copy_interp_bridge(struct linux_binprm *bprm)
{
	const char *arg = bprm->interp;

	return MCCTRL_COPY_STRING_KERNEL(arg, bprm);
}

int mcctrl_binfmt_copy_mcexec_bridge(struct linux_binprm *bprm)
{
	const char *arg = MCEXEC_PATH;

	return MCCTRL_COPY_STRING_KERNEL(arg, bprm);
}

int mcctrl_binfmt_change_interp_bridge(struct linux_binprm *bprm)
{
	return bprm_change_interp(MCEXEC_PATH, bprm);
}

int mcctrl_binfmt_dispatch_bridge(struct linux_binprm *bprm, void *file)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 19, 0)
	bprm->interpreter = file;
	return 0;
#else
	int rc;

	allow_write_access(bprm->file);
	fput(bprm->file);
	bprm->file = file;

	rc = MCCTRL_PREPARE_BINPRM(bprm);
	if (rc < 0)
		return rc;

	return search_binary_handler(bprm);
#endif
}
#endif

/* OS event notifier implementation */
#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_driver_find_os_bridge(int index)
{
	return ihk_host_find_os(index, NULL);
}

static int mcctrl_driver_prepare_channels_bridge(void *os)
{
	return prepare_ikc_channels((ihk_os_t)os);
}

static void mcctrl_driver_destroy_channels_bridge(void *os)
{
	destroy_ikc_channels((ihk_os_t)os);
}

static void mcctrl_driver_copy_user_call_proto_bridge(int index)
{
	memcpy(mcctrl_uc + index, &mcctrl_uc_proto, sizeof mcctrl_uc_proto);
}

static int mcctrl_driver_set_kernel_handlers_bridge(void *os)
{
	return ihk_os_set_kernel_call_handlers((ihk_os_t)os,
			&mcctrl_kernel_handlers);
}

static void mcctrl_driver_clear_kernel_handlers_bridge(void *os)
{
	ihk_os_clear_kernel_call_handlers((ihk_os_t)os);
}

static int mcctrl_driver_register_user_handlers_bridge(void *os, int index)
{
	return ihk_os_register_user_call_handlers((ihk_os_t)os,
			mcctrl_uc + index);
}

static void mcctrl_driver_unregister_user_handlers_bridge(void *os, int index)
{
	ihk_os_unregister_user_call_handlers((ihk_os_t)os,
			mcctrl_uc + index);
}

static void mcctrl_driver_procfs_init_bridge(int index)
{
	procfs_init(index);
}

static void mcctrl_driver_procfs_exit_bridge(int index)
{
	procfs_exit(index);
}

static void mcctrl_driver_pager_cleanup_bridge(void)
{
	pager_cleanup();
}

static void mcctrl_driver_sysfs_cleanup_bridge(void *os)
{
	sysfsm_cleanup((ihk_os_t)os);
}

static void mcctrl_driver_free_topology_info_bridge(void *os)
{
	free_topology_info((ihk_os_t)os);
}

static void mcctrl_driver_log_bridge(int stage, int index)
{
	switch (stage) {
	case 0:
		printk("mcctrl: error: OS ID %d couldn't be found\n", index);
		break;
	case 1:
		printk("mcctrl: error: preparing IKC channels for OS %d\n",
				index);
		break;
	case 2:
		printk("mcctrl: error: setting kernel callbacks for OS %d\n",
				index);
		break;
	case 3:
		printk("mcctrl: error: registering callbacks for OS %d\n",
				index);
		break;
	case 4:
		printk("mcctrl: OS ID %d boot event handled\n", index);
		break;
	case 5:
		printk("mcctrl: OS ID %d shutdown event handled\n", index);
		break;
	case 6:
		printk("mcctrl: error: registering OS notifier\n");
		break;
	case 7:
		printk("mcctrl: initialized successfully.\n");
		break;
	case 8:
		printk("mcctrl: warning: failed to deregister OS notifier??\n");
		break;
	case 9:
		printk("mcctrl: unregistered.\n");
		break;
	}
}

static const struct mcctrl_driver_boot_ops mcctrl_driver_boot_ops = {
	.find_os = mcctrl_driver_find_os_bridge,
	.set_os = mcctrl_driver_set_os_slot_bridge,
	.prepare_channels = mcctrl_driver_prepare_channels_bridge,
	.copy_user_call_proto = mcctrl_driver_copy_user_call_proto_bridge,
	.set_kernel_handlers = mcctrl_driver_set_kernel_handlers_bridge,
	.register_user_handlers = mcctrl_driver_register_user_handlers_bridge,
	.procfs_init = mcctrl_driver_procfs_init_bridge,
	.clear_kernel_handlers = mcctrl_driver_clear_kernel_handlers_bridge,
	.destroy_channels = mcctrl_driver_destroy_channels_bridge,
	.log = mcctrl_driver_log_bridge,
};

static const struct mcctrl_driver_shutdown_ops mcctrl_driver_shutdown_ops = {
	.get_os = mcctrl_driver_get_os_slot_bridge,
	.set_os = mcctrl_driver_set_os_slot_bridge,
	.pager_cleanup = mcctrl_driver_pager_cleanup_bridge,
	.sysfs_cleanup = mcctrl_driver_sysfs_cleanup_bridge,
	.free_topology_info = mcctrl_driver_free_topology_info_bridge,
	.unregister_user_handlers =
		mcctrl_driver_unregister_user_handlers_bridge,
	.clear_kernel_handlers = mcctrl_driver_clear_kernel_handlers_bridge,
	.destroy_channels = mcctrl_driver_destroy_channels_bridge,
	.procfs_exit = mcctrl_driver_procfs_exit_bridge,
	.log = mcctrl_driver_log_bridge,
};
#endif

int mcctrl_os_boot_notifier(int os_index)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_driver_boot_notifier_body_result(
			os_index, &mcctrl_driver_boot_ops);
#else
	int	rc;

	os[os_index] = ihk_host_find_os(os_index, NULL);
	if (!os[os_index]) {
		printk("mcctrl: error: OS ID %d couldn't be found\n", os_index);
		return -EINVAL;
	}

	if (prepare_ikc_channels(os[os_index]) != 0) {
		printk("mcctrl: error: preparing IKC channels for OS %d\n", os_index);

		os[os_index] = NULL;
		return -EFAULT;
	}

	memcpy(mcctrl_uc + os_index, &mcctrl_uc_proto, sizeof mcctrl_uc_proto);

	rc = ihk_os_set_kernel_call_handlers(os[os_index], &mcctrl_kernel_handlers);
	if (rc < 0) {
		printk("mcctrl: error: setting kernel callbacks for OS %d\n", os_index);
		goto error_cleanup_channels;
	}

	rc = ihk_os_register_user_call_handlers(os[os_index], mcctrl_uc + os_index);
	if (rc < 0) {
		printk("mcctrl: error: registering callbacks for OS %d\n", os_index);
		goto error_clear_kernel_handlers;
	}

	procfs_init(os_index);
	printk("mcctrl: OS ID %d boot event handled\n", os_index);

	return 0;

error_clear_kernel_handlers:
	ihk_os_clear_kernel_call_handlers(os[os_index]);
error_cleanup_channels:
	destroy_ikc_channels(os[os_index]);

	os[os_index] = NULL;
	return rc;
#endif
}

int mcctrl_os_shutdown_notifier(int os_index)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_driver_shutdown_notifier_body_result(
			os_index, &mcctrl_driver_shutdown_ops);
#else
	if (os[os_index]) {
		pager_cleanup();
		sysfsm_cleanup(os[os_index]);
		free_topology_info(os[os_index]);
		ihk_os_unregister_user_call_handlers(os[os_index], mcctrl_uc + os_index);
		ihk_os_clear_kernel_call_handlers(os[os_index]);
		destroy_ikc_channels(os[os_index]);
		procfs_exit(os_index);
	}

	os[os_index] = NULL;

	printk("mcctrl: OS ID %d shutdown event handled\n", os_index);
	return 0;
#endif
}

int mcctrl_os_alive()
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_driver_os_alive_body_result(
			OS_MAX_MINOR, mcctrl_driver_get_os_slot_bridge);
#else
	int i;

	for (i = 0; i < OS_MAX_MINOR; i++)
		if (os[i])
			return i;
	return -1;
#endif
}

static struct ihk_os_notifier_ops mcctrl_os_notifier_ops = {
	.boot = mcctrl_os_boot_notifier,
	.shutdown = mcctrl_os_shutdown_notifier,
};

static struct ihk_os_notifier mcctrl_os_notifier = {
	.ops = &mcctrl_os_notifier_ops,
};



int (*mcctrl_sys_mount)(char *dev_name, char *dir_name, char *type,
			unsigned long flags, void *data);
int (*mcctrl_sys_umount)(char *dir_name, int flags);
int (*mcctrl_sys_unshare)(unsigned long unshare_flags);
long (*mcctrl_sched_setaffinity)(pid_t pid, const struct cpumask *in_mask);
int (*mcctrl_sched_setscheduler_nocheck)(struct task_struct *p, int policy,
					 const struct sched_param *param);

ssize_t (*mcctrl_sys_readlinkat)(int dfd, const char *path, char *buf,
			       size_t bufsiz);
void (*mcctrl_zap_page_range)(struct vm_area_struct *vma,
			      unsigned long start,
			      unsigned long size,
			      struct zap_details *details);

struct inode_operations *mcctrl_hugetlbfs_inode_operations;

#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_driver_lookup_mount_bridge(void)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	return (void *)kallsyms_lookup_name("ksys_mount");
#else
	void *symbol = (void *)kallsyms_lookup_name("sys_mount");
#if defined(CONFIG_X86_64_SMP)
	if (!symbol)
		symbol = (void *)kallsyms_lookup_name("__x64_sys_mount");
#endif
	return symbol;
#endif
}

static void mcctrl_driver_set_mount_bridge(void *symbol)
{
	mcctrl_sys_mount = symbol;
}

static void *mcctrl_driver_lookup_umount_bridge(void)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	return (void *)kallsyms_lookup_name("ksys_umount");
#else
	void *symbol = (void *)kallsyms_lookup_name("sys_umount");
#if defined(CONFIG_X86_64_SMP)
	if (!symbol)
		symbol = (void *)kallsyms_lookup_name("__x64_sys_umount");
#endif
	return symbol;
#endif
}

static void mcctrl_driver_set_umount_bridge(void *symbol)
{
	mcctrl_sys_umount = symbol;
}

static void *mcctrl_driver_lookup_unshare_bridge(void)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	return (void *)kallsyms_lookup_name("ksys_unshare");
#else
	void *symbol = (void *)kallsyms_lookup_name("sys_unshare");
#if defined(CONFIG_X86_64_SMP)
	if (!symbol)
		symbol = (void *)kallsyms_lookup_name("__x64_sys_unshare");
#endif
	return symbol;
#endif
}

static void mcctrl_driver_set_unshare_bridge(void *symbol)
{
	mcctrl_sys_unshare = symbol;
}

static void *mcctrl_driver_lookup_sched_setaffinity_bridge(void)
{
	return (void *)kallsyms_lookup_name("sched_setaffinity");
}

static void mcctrl_driver_set_sched_setaffinity_bridge(void *symbol)
{
	mcctrl_sched_setaffinity = symbol;
}

static void *mcctrl_driver_lookup_sched_setscheduler_nocheck_bridge(void)
{
	return (void *)kallsyms_lookup_name("sched_setscheduler_nocheck");
}

static void mcctrl_driver_set_sched_setscheduler_nocheck_bridge(void *symbol)
{
	mcctrl_sched_setscheduler_nocheck = symbol;
}

static void *mcctrl_driver_lookup_readlinkat_bridge(void)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	return (void *)kallsyms_lookup_name("do_readlinkat");
#else
	void *symbol = (void *)kallsyms_lookup_name("sys_readlinkat");
#if defined(CONFIG_X86_64_SMP)
	if (!symbol)
		symbol = (void *)kallsyms_lookup_name("__x64_sys_readlinkat");
#endif
	return symbol;
#endif
}

static void mcctrl_driver_set_readlinkat_bridge(void *symbol)
{
	mcctrl_sys_readlinkat = symbol;
}

static void *mcctrl_driver_lookup_zap_page_range_bridge(void)
{
	return (void *)kallsyms_lookup_name("zap_page_range");
}

static void mcctrl_driver_set_zap_page_range_bridge(void *symbol)
{
	mcctrl_zap_page_range = symbol;
}

static void *mcctrl_driver_lookup_hugetlbfs_inode_operations_bridge(void)
{
	return (void *)kallsyms_lookup_name("hugetlbfs_inode_operations");
}

static void mcctrl_driver_set_hugetlbfs_inode_operations_bridge(void *symbol)
{
	mcctrl_hugetlbfs_inode_operations = symbol;
}

static int mcctrl_driver_warn_missing_symbol_bridge(void *symbol)
{
	return WARN_ON(!symbol);
}

static int mcctrl_driver_arch_symbols_init_bridge(void)
{
	return arch_symbols_init();
}

static const struct mcctrl_driver_symbols_ops mcctrl_driver_symbols_ops = {
	.lookup_mount = mcctrl_driver_lookup_mount_bridge,
	.set_mount = mcctrl_driver_set_mount_bridge,
	.lookup_umount = mcctrl_driver_lookup_umount_bridge,
	.set_umount = mcctrl_driver_set_umount_bridge,
	.lookup_unshare = mcctrl_driver_lookup_unshare_bridge,
	.set_unshare = mcctrl_driver_set_unshare_bridge,
	.lookup_sched_setaffinity =
		mcctrl_driver_lookup_sched_setaffinity_bridge,
	.set_sched_setaffinity =
		mcctrl_driver_set_sched_setaffinity_bridge,
	.lookup_sched_setscheduler_nocheck =
		mcctrl_driver_lookup_sched_setscheduler_nocheck_bridge,
	.set_sched_setscheduler_nocheck =
		mcctrl_driver_set_sched_setscheduler_nocheck_bridge,
	.lookup_readlinkat = mcctrl_driver_lookup_readlinkat_bridge,
	.set_readlinkat = mcctrl_driver_set_readlinkat_bridge,
	.lookup_zap_page_range =
		mcctrl_driver_lookup_zap_page_range_bridge,
	.set_zap_page_range = mcctrl_driver_set_zap_page_range_bridge,
	.lookup_hugetlbfs_inode_operations =
		mcctrl_driver_lookup_hugetlbfs_inode_operations_bridge,
	.set_hugetlbfs_inode_operations =
		mcctrl_driver_set_hugetlbfs_inode_operations_bridge,
	.warn_missing = mcctrl_driver_warn_missing_symbol_bridge,
	.arch_symbols_init = mcctrl_driver_arch_symbols_init_bridge,
};
#endif

static int symbols_init(void)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_driver_symbols_init_body_result(
			&mcctrl_driver_symbols_ops);
#else
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	mcctrl_sys_mount = (void *) kallsyms_lookup_name("ksys_mount");
#else
	mcctrl_sys_mount = (void *) kallsyms_lookup_name("sys_mount");
#if defined(CONFIG_X86_64_SMP)
	if (!mcctrl_sys_mount)
		mcctrl_sys_mount =
			(void *) kallsyms_lookup_name("__x64_sys_mount");
#endif
#endif
	if (WARN_ON(!mcctrl_sys_mount))
		return -EFAULT;

#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	mcctrl_sys_umount = (void *) kallsyms_lookup_name("ksys_umount");
#else
	mcctrl_sys_umount = (void *) kallsyms_lookup_name("sys_umount");
#if defined(CONFIG_X86_64_SMP)
	if (!mcctrl_sys_umount)
		mcctrl_sys_umount =
			(void *) kallsyms_lookup_name("__x64_sys_umount");
#endif
#endif
	if (WARN_ON(!mcctrl_sys_umount))
		return -EFAULT;

#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	mcctrl_sys_unshare = (void *) kallsyms_lookup_name("ksys_unshare");
#else
	mcctrl_sys_unshare = (void *) kallsyms_lookup_name("sys_unshare");
#if defined(CONFIG_X86_64_SMP)
	if (!mcctrl_sys_unshare)
		mcctrl_sys_unshare =
			(void *) kallsyms_lookup_name("__x64_sys_unshare");
#endif
#endif
	if (WARN_ON(!mcctrl_sys_unshare))
		return -EFAULT;

	mcctrl_sched_setaffinity =
		(void *) kallsyms_lookup_name("sched_setaffinity");
	if (WARN_ON(!mcctrl_sched_setaffinity))
		return -EFAULT;

	mcctrl_sched_setscheduler_nocheck =
		(void *) kallsyms_lookup_name("sched_setscheduler_nocheck");
	if (WARN_ON(!mcctrl_sched_setscheduler_nocheck))
		return -EFAULT;

#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,17,0)
	mcctrl_sys_readlinkat = (void *)kallsyms_lookup_name("do_readlinkat");
#else
	mcctrl_sys_readlinkat = (void *)kallsyms_lookup_name("sys_readlinkat");
#if defined(CONFIG_X86_64_SMP)
	if (!mcctrl_sys_readlinkat)
		mcctrl_sys_readlinkat =
			(void *) kallsyms_lookup_name("__x64_sys_readlinkat");
#endif
#endif
	if (WARN_ON(!mcctrl_sys_readlinkat))
		return -EFAULT;

	mcctrl_zap_page_range =
		(void *) kallsyms_lookup_name("zap_page_range");
	if (WARN_ON(!mcctrl_zap_page_range))
		return -EFAULT;

	mcctrl_hugetlbfs_inode_operations =
		(void *) kallsyms_lookup_name("hugetlbfs_inode_operations");
	if (WARN_ON(!mcctrl_hugetlbfs_inode_operations))
		return -EFAULT;

	return arch_symbols_init();
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static void mcctrl_driver_syscall_init_bridge(void)
{
#ifndef DO_USER_MODE
	mcctrl_syscall_init();
#endif
}

static void mcctrl_driver_binfmt_init_bridge(void)
{
	binfmt_mcexec_init();
}

static void mcctrl_driver_binfmt_exit_bridge(void)
{
	binfmt_mcexec_exit();
}

static void mcctrl_driver_tofu_hash_init_bridge(void)
{
#ifdef ENABLE_TOFU
	mcctrl_file_to_pidfd_hash_init();
#endif
}

static void mcctrl_driver_tofu_hijack_bridge(void)
{
#ifdef ENABLE_TOFU
	mcctrl_tofu_hijack_release_handlers();
#endif
}

static void mcctrl_driver_tofu_restore_bridge(void)
{
#ifdef ENABLE_TOFU
	mcctrl_tofu_restore_release_handlers();
#endif
}

static int mcctrl_driver_symbols_init_bridge(void)
{
	return symbols_init();
}

static int mcctrl_driver_register_notifier_bridge(void)
{
	return ihk_host_register_os_notifier(&mcctrl_os_notifier);
}

static int mcctrl_driver_deregister_notifier_bridge(void)
{
	return ihk_host_deregister_os_notifier(&mcctrl_os_notifier);
}

static void mcctrl_driver_uti_finalize_bridge(void)
{
	uti_attr_finalize();
}

static const struct mcctrl_driver_module_ops mcctrl_driver_module_ops = {
	.syscall_init = mcctrl_driver_syscall_init_bridge,
	.set_os = mcctrl_driver_set_os_slot_bridge,
	.binfmt_init = mcctrl_driver_binfmt_init_bridge,
	.tofu_hash_init = mcctrl_driver_tofu_hash_init_bridge,
	.symbols_init = mcctrl_driver_symbols_init_bridge,
	.tofu_hijack = mcctrl_driver_tofu_hijack_bridge,
	.register_notifier = mcctrl_driver_register_notifier_bridge,
	.binfmt_exit = mcctrl_driver_binfmt_exit_bridge,
	.deregister_notifier = mcctrl_driver_deregister_notifier_bridge,
	.uti_finalize = mcctrl_driver_uti_finalize_bridge,
	.tofu_restore = mcctrl_driver_tofu_restore_bridge,
	.log = mcctrl_driver_log_bridge,
};
#endif

static int __init mcctrl_init(void)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_driver_init_body_result(
			OS_MAX_MINOR, &mcctrl_driver_module_ops);
#else
	int ret = 0;
	int i;

#ifndef DO_USER_MODE
	mcctrl_syscall_init();
#endif

	for (i = 0; i < OS_MAX_MINOR; ++i) {
		os[i] = NULL;
	}

	binfmt_mcexec_init();
#ifdef ENABLE_TOFU
	mcctrl_file_to_pidfd_hash_init();
#endif

	if ((ret = symbols_init()))
		goto error;

#ifdef ENABLE_TOFU
	mcctrl_tofu_hijack_release_handlers();
#endif

	if ((ret = ihk_host_register_os_notifier(&mcctrl_os_notifier)) != 0) {
		printk("mcctrl: error: registering OS notifier\n");
		goto error;
	}

	printk("mcctrl: initialized successfully.\n");
	return ret;

error:
	binfmt_mcexec_exit();

	return ret;
#endif
}

static void __exit mcctrl_exit(void)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_driver_exit_body_result(&mcctrl_driver_module_ops);
#else
	if (ihk_host_deregister_os_notifier(&mcctrl_os_notifier) != 0) {
		printk("mcctrl: warning: failed to deregister OS notifier??\n");
	}

	binfmt_mcexec_exit();
	uti_attr_finalize();
#ifdef ENABLE_TOFU
	mcctrl_tofu_restore_release_handlers();
#endif

	printk("mcctrl: unregistered.\n");
#endif
}

MODULE_LICENSE("GPL v2");
module_init(mcctrl_init);
module_exit(mcctrl_exit);
