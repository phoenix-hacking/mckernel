/**
 * \file procfs.c
 *  License details are found in the file LICENSE.
 * \brief
 *  mcctrl procfs
 * \author Naoki Hamada <nao@axe.bz> \par
 * 	Copyright (C) 2014  AXE, Inc.
 */
/*
 * HISTORY:
 */
/* procfs.c COPYRIGHT FUJITSU LIMITED 2016-2017 */

#include <linux/slab.h>
#include <linux/string.h>
#include <linux/proc_fs.h>
#include <linux/list.h>
#include <linux/uaccess.h>
#include <linux/fs.h>
#include <linux/resource.h>
#include <linux/interrupt.h>
#include <linux/cred.h>
#include "mcctrl.h"
#include <linux/version.h>
#include <linux/semaphore.h>
#include <mcctrl_rust.h>

//#define PROCFS_DEBUG

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 4, 0)
#define MCCTRL_DEFINE_SEMAPHORE(name) DEFINE_SEMAPHORE(name, 1)
#else
#define MCCTRL_DEFINE_SEMAPHORE(name) DEFINE_SEMAPHORE(name)
#endif

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 17, 0)
#define MCCTRL_PDE_DATA(inode) pde_data(inode)
#else
#define MCCTRL_PDE_DATA(inode) PDE_DATA(inode)
#endif

#ifdef PROCFS_DEBUG
#define	dprintk(...)	printk(__VA_ARGS__)
#else
#define	dprintk(...)
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,5,0)
typedef uid_t kuid_t;
typedef gid_t kgid_t;
#endif

struct procfs_entry {
	char *name;
	mode_t mode;
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
	const struct proc_ops *fops;
#else
	const struct file_operations *fops;
#endif
};

#define NOD(NAME, MODE, FOP) {				\
	.name = (NAME),					\
	.mode = MODE,					\
	.fops  = FOP,					\
}
#define PROC_DIR(NAME, MODE)				\
	NOD(NAME, (S_IFDIR|(MODE)), NULL)
#define PROC_REG(NAME, MODE, fops)			\
	NOD(NAME, (S_IFREG|(MODE)), fops)
#define PROC_TERM					\
	NOD(NULL, 0, NULL)

static const struct procfs_entry tid_entry_stuff[];
static const struct procfs_entry pid_entry_stuff[];
static const struct procfs_entry base_entry_stuff[];
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
static const struct proc_ops mckernel_forward_ro;
static const struct proc_ops mckernel_forward;
#else
static const struct file_operations mckernel_forward_ro;
static const struct file_operations mckernel_forward;
#endif

static ssize_t mckernel_procfs_read(struct file *file, char __user *buf, 
		size_t nbytes, loff_t *ppos);

/* A private data for the procfs driver. */
struct procfs_list_entry;

struct procfs_list_entry {
	struct list_head list;
	struct proc_dir_entry *entry;
	struct procfs_list_entry *parent;
	struct list_head children;
	int osnum;
	char *data;
	char name[];
};

/*
 * In the procfs_file_list, mckenrel procfs files are
 * listed in the manner that the leaf file is located 
 * always nearer to the list top than its parent node 
 * file.
 */
LIST_HEAD(procfs_file_list);
MCCTRL_DEFINE_SEMAPHORE(procfs_file_list_lock);

#ifdef MCCTRL_RUST_HELPERS
static const char *
mcctrl_procfs_list_name_bridge(const void *entry)
{
	return ((const struct procfs_list_entry *)entry)->name;
}

static void *
mcctrl_procfs_list_parent_bridge(const void *entry)
{
	return ((const struct procfs_list_entry *)entry)->parent;
}

static void *
mcctrl_procfs_first_child_bridge(void *parent)
{
	struct list_head *list;

	if (parent)
		list = &((struct procfs_list_entry *)parent)->children;
	else
		list = &procfs_file_list;
	if (list_empty(list))
		return NULL;
	return list_first_entry(list, struct procfs_list_entry, list);
}

static void *
mcctrl_procfs_next_child_bridge(void *parent, void *entry)
{
	struct list_head *list;
	struct list_head *next = ((struct procfs_list_entry *)entry)->list.next;

	if (parent)
		list = &((struct procfs_list_entry *)parent)->children;
	else
		list = &procfs_file_list;
	if (next == list)
		return NULL;
	return list_entry(next, struct procfs_list_entry, list);
}

static void *mcctrl_procfs_find_entry_bridge(void *parent, const char *name);
static void mcctrl_procfs_delete_entry_bridge(void *entry);

static void *
mcctrl_procfs_alloc_entry_bridge(unsigned long size)
{
	return kmalloc(size, GFP_KERNEL);
}

static void
mcctrl_procfs_init_entry_bridge(void *entry, const char *name)
{
	struct procfs_list_entry *e = entry;

	memset(e, '\0', sizeof(*e));
	INIT_LIST_HEAD(&e->children);
	strcpy(e->name, name);
}

static void *
mcctrl_procfs_create_pde_bridge(void *parent, const char *name,
				unsigned int mode, const void *uid,
				const void *gid, const void *opaque,
				void *entry)
{
	struct procfs_list_entry *e = entry;
	struct proc_dir_entry *pde;
	struct proc_dir_entry *parent_pde = NULL;
	int f_mode = mode & 0777;

	if (parent)
		parent_pde = ((struct procfs_list_entry *)parent)->entry;

	if (mode & S_IFDIR) {
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
		pde = proc_mkdir(name, parent_pde);
#else
		pde = proc_mkdir_data(name, f_mode, parent_pde, e);
#endif
	}
	else if ((mode & S_IFLNK) == S_IFLNK) {
		pde = proc_symlink(name, parent_pde, (char *)opaque);
	}
	else {
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
		const struct proc_ops *fop;
#else
		const struct file_operations *fop;
#endif

		if(opaque)
			fop = (typeof(fop))opaque;
		else if(mode & S_IWUSR)
			fop = &mckernel_forward;
		else
			fop = &mckernel_forward_ro;

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
		pde = create_proc_entry(name, f_mode, parent_pde);
		if(pde)
			pde->proc_fops = fop;
#else
		pde = proc_create_data(name, f_mode, parent_pde, fop, e);
		if(pde)
			proc_set_user(pde, *(const kuid_t *)uid,
				      *(const kgid_t *)gid);
#endif
	}

	return pde;
}

static void
mcctrl_procfs_commit_entry_bridge(void *entry, void *parent, void *pde,
				  const void *uid, const void *gid)
{
	struct procfs_list_entry *e = entry;
	struct procfs_list_entry *p = parent;

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	((struct proc_dir_entry *)pde)->uid = *(const kuid_t *)uid;
	((struct proc_dir_entry *)pde)->gid = *(const kgid_t *)gid;
	((struct proc_dir_entry *)pde)->data = e;
#else
	(void)uid;
	(void)gid;
#endif
	if(p)
		e->osnum = p->osnum;
	e->entry = pde;
	e->parent = p;
	list_add(&(e->list), p ? &(p->children) : &procfs_file_list);
}

static void
mcctrl_procfs_free_entry_bridge(void *entry)
{
	kfree(entry);
}

static void
mcctrl_procfs_unlink_entry_bridge(void *entry)
{
	list_del(&((struct procfs_list_entry *)entry)->list);
}

static void
mcctrl_procfs_remove_proc_entry_bridge(void *entry)
{
	struct procfs_list_entry *e = entry;

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	if (e->entry) {
		e->entry->read_proc = NULL;
		e->entry->data = NULL;
	}
#endif
	remove_proc_entry(e->name, e->parent ? e->parent->entry : NULL);
}

static void *
mcctrl_procfs_entry_data_bridge(void *entry)
{
	return ((struct procfs_list_entry *)entry)->data;
}

static void
mcctrl_procfs_add_alloc_failed_bridge(void)
{
	kprintf("ERROR: not enough memory to create PROCFS entry.\n");
}

static void
mcctrl_procfs_add_create_failed_bridge(const char *name)
{
	kprintf("ERROR: cannot create a PROCFS entry for %s.\n", name);
}
#endif

static char *
getpath(struct procfs_list_entry *e, char *buf, int bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_getpath_body_result(
		e, buf, bufsize,
		mcctrl_procfs_list_name_bridge,
		mcctrl_procfs_list_parent_bridge);
#else
	char	*w = buf + bufsize - 1;

	*w = '\0';
	for(;;){
		int l = strlen(e->name);
		w -= l;
		memcpy(w, e->name, l);
		e = e->parent;
		if(!e)
			return w;
		w--;
		*w = '/';
	}
#endif
}

static struct procfs_list_entry *
find_procfs_entry(struct procfs_list_entry *parent, const char *name)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_find_entry_body_result(
		parent, name, mcctrl_procfs_first_child_bridge,
		mcctrl_procfs_next_child_bridge,
		mcctrl_procfs_list_name_bridge);
#else
	struct list_head *list;
	struct procfs_list_entry *e;

	if(parent == NULL)
		list = &procfs_file_list;
	else
		list = &parent->children;

	list_for_each_entry(e, list, list) {
		if(!strcmp(e->name, name))
			return e;
	}

	return NULL;
#endif
}

static void
delete_procfs_entries(struct procfs_list_entry *top)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_delete_entries_body_result(
		top, mcctrl_procfs_first_child_bridge,
		mcctrl_procfs_delete_entry_bridge,
		mcctrl_procfs_unlink_entry_bridge,
		mcctrl_procfs_remove_proc_entry_bridge,
		mcctrl_procfs_entry_data_bridge,
		mcctrl_procfs_free_entry_bridge);
#else
	struct procfs_list_entry *e = NULL;
	struct procfs_list_entry *n;

	list_del(&top->list);

	list_for_each_entry_safe(e, n, &top->children, list) {
		delete_procfs_entries(e);
	}

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	if (e) {
		e->entry->read_proc = NULL;
		e->entry->data = NULL;
	}
#endif
	remove_proc_entry(top->name, top->parent? top->parent->entry: NULL);
	if(top->data)
		kfree(top->data);
	kfree(top);
#endif
}

static struct procfs_list_entry *
add_procfs_entry(struct procfs_list_entry *parent, const char *name, int mode,
                 kuid_t uid, kgid_t gid, const void *opaque)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_add_entry_body_result(
		parent, name, mode, &uid, &gid, opaque, sizeof(*parent),
		mcctrl_procfs_find_entry_bridge,
		mcctrl_procfs_delete_entry_bridge,
		mcctrl_procfs_alloc_entry_bridge,
		mcctrl_procfs_init_entry_bridge,
		mcctrl_procfs_create_pde_bridge,
		mcctrl_procfs_commit_entry_bridge,
		mcctrl_procfs_free_entry_bridge,
		mcctrl_procfs_add_alloc_failed_bridge,
		mcctrl_procfs_add_create_failed_bridge);
#else
	struct procfs_list_entry *e = find_procfs_entry(parent, name);
	struct proc_dir_entry *pde;
	struct proc_dir_entry *parent_pde = NULL;
	int f_mode = mode & 0777;

	if(e)
		delete_procfs_entries(e);

	e = kmalloc(sizeof(struct procfs_list_entry) + strlen(name) + 1,
	            GFP_KERNEL);
	if(!e){
		kprintf("ERROR: not enough memory to create PROCFS entry.\n");
		return NULL;
	}
	memset(e, '\0', sizeof(struct procfs_list_entry));
	INIT_LIST_HEAD(&e->children);
	strcpy(e->name, name);

	if(parent)
		parent_pde = parent->entry;

	if (mode & S_IFDIR) {
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
		pde = proc_mkdir(name, parent_pde);
#else
		pde = proc_mkdir_data(name, f_mode, parent_pde, e);
#endif
	}
	else if ((mode & S_IFLNK) == S_IFLNK) {
		pde = proc_symlink(name, parent_pde, (char *)opaque);
	}
	else {
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
		const struct proc_ops *fop;
#else
		const struct file_operations *fop;
#endif

		if(opaque)
			fop = (typeof(fop))opaque;
		else if(mode & S_IWUSR)
			fop = &mckernel_forward;
		else
			fop = &mckernel_forward_ro;

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
		pde = create_proc_entry(name, f_mode, parent_pde);
		if(pde)
			pde->proc_fops = fop;
#else
		pde = proc_create_data(name, f_mode, parent_pde, fop, e);
		if(pde)
			proc_set_user(pde, uid, gid);
#endif
	}
	if(!pde){
		kprintf("ERROR: cannot create a PROCFS entry for %s.\n", name);
		kfree(e);
		return NULL;
	}
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	pde->uid = uid;
	pde->gid = gid;
	pde->data = e;
#endif

	if(parent)
		e->osnum = parent->osnum;
	e->entry = pde;
	e->parent = parent;
	list_add(&(e->list), parent? &(parent->children): &procfs_file_list);

	return e;
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static const char *
mcctrl_procfs_entry_table_name_bridge(const void *entry)
{
	return ((const struct procfs_entry *)entry)->name;
}

static unsigned int
mcctrl_procfs_entry_table_mode_bridge(const void *entry)
{
	return ((const struct procfs_entry *)entry)->mode;
}

static const void *
mcctrl_procfs_entry_table_fops_bridge(const void *entry)
{
	return ((const struct procfs_entry *)entry)->fops;
}

static const void *
mcctrl_procfs_entry_table_next_bridge(const void *entry, unsigned long size)
{
	return (const char *)entry + size;
}

static void
mcctrl_procfs_add_entry_with_ids_bridge(void *parent, const char *name,
					unsigned int mode, const void *fops,
					const void *uid, const void *gid)
{
	add_procfs_entry(parent, name, mode, *(const kuid_t *)uid,
			 *(const kgid_t *)gid, fops);
}
#endif

static void
add_procfs_entries(struct procfs_list_entry *parent,
                   const struct procfs_entry *entries, kuid_t uid, kgid_t gid)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_add_entries_body_result(
		parent, entries, sizeof(*entries), &uid, &gid,
		mcctrl_procfs_entry_table_name_bridge,
		mcctrl_procfs_entry_table_mode_bridge,
		mcctrl_procfs_entry_table_fops_bridge,
		mcctrl_procfs_entry_table_next_bridge,
		mcctrl_procfs_add_entry_with_ids_bridge);
#else
	const struct procfs_entry *p;

	for(p = entries; p->name; p++){
		add_procfs_entry(parent, p->name, p->mode, uid, gid, p->fops);
	}
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static void
mcctrl_procfs_rcu_read_lock_bridge(void)
{
	rcu_read_lock();
}

static void
mcctrl_procfs_rcu_read_unlock_bridge(void)
{
	rcu_read_unlock();
}

static void *
mcctrl_procfs_find_vpid_bridge(int pid)
{
	return find_vpid(pid);
}

static void *
mcctrl_procfs_pid_task_bridge(void *pid, int type)
{
	return pid_task(pid, (enum pid_type)type);
}

static void *
mcctrl_procfs_task_cred_bridge(void *task)
{
	return (void *)__task_cred((struct task_struct *)task);
}
#endif

static const struct cred *
get_pid_cred(int pid)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_get_pid_cred_body_result(
		pid, PIDTYPE_PID, mcctrl_procfs_rcu_read_lock_bridge,
		mcctrl_procfs_rcu_read_unlock_bridge,
		mcctrl_procfs_find_vpid_bridge,
		mcctrl_procfs_pid_task_bridge,
		mcctrl_procfs_task_cred_bridge);
#else
	struct task_struct *task = NULL;

	if (pid > 0) {
		rcu_read_lock();
		task = pid_task(find_vpid(pid), PIDTYPE_PID);
		rcu_read_unlock();
		if (task) {
			return __task_cred(task);
		}
	}
	return NULL;
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_procfs_find_entry_bridge(void *parent, const char *name)
{
	return find_procfs_entry(parent, name);
}

static void *
mcctrl_procfs_add_dir_entry_bridge(void *parent, const char *name, int mode)
{
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	return add_procfs_entry(parent, name, mode, uid, gid, NULL);
}

static void
mcctrl_procfs_set_osnum_bridge(void *entry, int osnum)
{
	((struct procfs_list_entry *)entry)->osnum = osnum;
}
#endif

static struct procfs_list_entry *
find_base_entry(int osnum)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_find_base_entry_body_result(
		osnum, mcctrl_format_mcos_name,
		mcctrl_procfs_find_entry_bridge);
#else
	char name[12];

	mcctrl_format_mcos_name(name, sizeof(name), osnum);
	return find_procfs_entry(NULL, name);
#endif
}

static struct procfs_list_entry *
find_pid_entry(int osnum, int pid)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_find_pid_entry_body_result(
		osnum, pid, mcctrl_format_mcos_name,
		mcctrl_format_decimal_name,
		mcctrl_procfs_find_entry_bridge);
#else
	struct procfs_list_entry *e;
	char name[12];

	if(!(e = find_base_entry(osnum)))
		return NULL;
	mcctrl_format_decimal_name(name, sizeof(name), pid);
	return find_procfs_entry(e, name);
#endif
}

static struct procfs_list_entry *
find_tid_entry(int osnum, int pid, int tid)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_find_tid_entry_body_result(
		osnum, pid, tid, mcctrl_format_mcos_name,
		mcctrl_format_decimal_name,
		mcctrl_procfs_find_entry_bridge);
#else
	struct procfs_list_entry *e;
	char name[12];

	if(!(e = find_pid_entry(osnum, pid)))
		return NULL;
	if(!(e = find_procfs_entry(e, "task")))
		return NULL;
	mcctrl_format_decimal_name(name, sizeof(name), tid);
	return find_procfs_entry(e, name);
#endif
}

static struct procfs_list_entry *
get_base_entry(int osnum)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_get_base_entry_body_result(
		osnum, mcctrl_format_mcos_name,
		mcctrl_procfs_find_entry_bridge,
		mcctrl_procfs_add_dir_entry_bridge,
		mcctrl_procfs_set_osnum_bridge);
#else
	struct procfs_list_entry *e;
	char name[12];
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	mcctrl_format_mcos_name(name, sizeof(name), osnum);
	e = find_procfs_entry(NULL, name);
	if(!e){
		e = add_procfs_entry(NULL, name, S_IFDIR | 0555,
		                     uid, gid, NULL);
		if (!e)
			return NULL;
		e->osnum = osnum;
	}
	return e;
#endif
}

static struct procfs_list_entry *
get_pid_entry(int osnum, int pid)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_get_pid_entry_body_result(
		osnum, pid, mcctrl_format_mcos_name,
		mcctrl_format_decimal_name,
		mcctrl_procfs_find_entry_bridge,
		mcctrl_procfs_add_dir_entry_bridge);
#else
	struct procfs_list_entry *parent;
	struct procfs_list_entry *e;
	char name[12];
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	mcctrl_format_mcos_name(name, sizeof(name), osnum);
	if(!(parent = find_procfs_entry(NULL, name)))
		return NULL;
	mcctrl_format_decimal_name(name, sizeof(name), pid);
	e = find_procfs_entry(parent, name);
	if(!e)
		e = add_procfs_entry(parent, name, S_IFDIR | 0555,
		                     uid, gid, NULL);
	return e;
#endif
}

static struct procfs_list_entry *
get_tid_entry(int osnum, int pid, int tid)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_get_tid_entry_body_result(
		osnum, pid, tid, mcctrl_format_mcos_name,
		mcctrl_format_decimal_name,
		mcctrl_procfs_find_entry_bridge,
		mcctrl_procfs_add_dir_entry_bridge);
#else
	struct procfs_list_entry *parent;
	struct procfs_list_entry *e;
	char name[12];
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	mcctrl_format_mcos_name(name, sizeof(name), osnum);
	if(!(parent = find_procfs_entry(NULL, name)))
		return NULL;
	mcctrl_format_decimal_name(name, sizeof(name), pid);
	if(!(parent = find_procfs_entry(parent, name)))
		return NULL;
	if(!(parent = find_procfs_entry(parent, "task")))
		return NULL;
	mcctrl_format_decimal_name(name, sizeof(name), tid);
	e = find_procfs_entry(parent, name);
	if(!e)
		e = add_procfs_entry(parent, name, S_IFDIR | 0555,
		                     uid, gid, NULL);
	return e;
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_procfs_find_tid_entry_bridge(int osnum, int pid, int tid);
static void *mcctrl_procfs_get_tid_entry_bridge(int osnum, int pid, int tid);
static void mcctrl_procfs_add_tid_entries_bridge(void *parent, void *credp);
static void *mcctrl_procfs_find_exe_data_bridge(void *parent);
static void mcctrl_procfs_add_exe_symlink_bridge(void *parent, void *target,
						void *credp);
#endif

static void
_add_tid_entry(int osnum, int pid, int tid, const struct cred *cred)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_add_tid_with_cred_body_result(
		osnum, pid, tid, (void *)cred,
		mcctrl_procfs_get_tid_entry_bridge,
		mcctrl_procfs_add_tid_entries_bridge,
		mcctrl_procfs_find_exe_data_bridge,
		mcctrl_procfs_add_exe_symlink_bridge);
#else
	struct procfs_list_entry *parent;
	struct procfs_list_entry *exe;

	parent = get_tid_entry(osnum, pid, tid);
	if(parent){
		add_procfs_entries(parent, tid_entry_stuff,
		                   cred->uid, cred->gid);
		exe = find_procfs_entry(parent->parent->parent, "exe");
		if(exe){
			add_procfs_entry(parent, "exe", S_IFLNK | 0777,
			                 cred->uid, cred->gid, exe->data);
		}
		
	}
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_procfs_get_pid_cred_bridge(int pid)
{
	return (void *)get_pid_cred(pid);
}

static void
mcctrl_procfs_lock_bridge(void)
{
	down(&procfs_file_list_lock);
}

static void
mcctrl_procfs_unlock_bridge(void)
{
	up(&procfs_file_list_lock);
}

static void *
mcctrl_procfs_find_base_entry_bridge(int osnum)
{
	return find_base_entry(osnum);
}

static void *
mcctrl_procfs_find_pid_entry_bridge(int osnum, int pid)
{
	return find_pid_entry(osnum, pid);
}

static void *
mcctrl_procfs_find_tid_entry_bridge(int osnum, int pid, int tid)
{
	return find_tid_entry(osnum, pid, tid);
}

static void *
mcctrl_procfs_get_base_entry_bridge(int osnum)
{
	return get_base_entry(osnum);
}

static void *
mcctrl_procfs_get_pid_entry_bridge(int osnum, int pid)
{
	return get_pid_entry(osnum, pid);
}

static void *
mcctrl_procfs_get_tid_entry_bridge(int osnum, int pid, int tid)
{
	return get_tid_entry(osnum, pid, tid);
}

static void
mcctrl_procfs_add_pid_entries_bridge(void *parent, void *credp)
{
	const struct cred *cred = credp;

	add_procfs_entries(parent, pid_entry_stuff, cred->uid, cred->gid);
}

static void
mcctrl_procfs_add_tid_entries_bridge(void *parent, void *credp)
{
	const struct cred *cred = credp;

	add_procfs_entries(parent, tid_entry_stuff, cred->uid, cred->gid);
}

static void
mcctrl_procfs_add_base_entries_bridge(void *parent)
{
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	add_procfs_entries(parent, base_entry_stuff, uid, gid);
}

static void
mcctrl_procfs_add_tid_with_cred_bridge(int osnum, int pid, int tid,
				       void *cred)
{
	_add_tid_entry(osnum, pid, tid, cred);
}

static void
mcctrl_procfs_delete_entry_bridge(void *entry)
{
	delete_procfs_entries(entry);
}

static void *
mcctrl_procfs_find_exe_data_bridge(void *parent)
{
	struct procfs_list_entry *p = parent;
	struct procfs_list_entry *exe;

	exe = find_procfs_entry(p->parent->parent, "exe");
	return exe ? exe->data : NULL;
}

static void
mcctrl_procfs_add_exe_symlink_bridge(void *parent, void *target, void *credp)
{
	const struct cred *cred = credp;

	add_procfs_entry(parent, "exe", S_IFLNK | 0777, cred->uid, cred->gid,
			 target);
}

static void *
mcctrl_procfs_add_pid_exe_bridge(void *parent, const char *path)
{
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	return add_procfs_entry(parent, "exe", S_IFLNK | 0777, uid, gid,
				path);
}

static void
mcctrl_procfs_store_exe_path_bridge(void *entry, const char *path)
{
	struct procfs_list_entry *e = entry;

	e->data = kmalloc(strlen(path) + 1, GFP_KERNEL);
	strcpy(e->data, path);
}

static void
mcctrl_procfs_add_task_exe_links_bridge(void *pid_parent, const char *path)
{
	struct procfs_list_entry *task;
	struct procfs_list_entry *parent;

	task = find_procfs_entry(pid_parent, "task");
	list_for_each_entry(parent, &task->children, list) {
		add_procfs_entry(parent, "exe", S_IFLNK | 0777,
				 KUIDT_INIT(0), KGIDT_INIT(0), path);
	}
}
#endif

void
add_tid_entry(int osnum, int pid, int tid)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_add_tid_entry_body_result(
		osnum, pid, tid, mcctrl_procfs_get_pid_cred_bridge,
		mcctrl_procfs_lock_bridge, mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_find_pid_entry_bridge,
		mcctrl_procfs_get_pid_entry_bridge,
		mcctrl_procfs_add_pid_entries_bridge,
		mcctrl_procfs_add_tid_with_cred_bridge);
#else
	const struct cred *cred = get_pid_cred(pid);
	struct procfs_list_entry *parent;

	if(!cred)
		return;
	down(&procfs_file_list_lock);
	parent = find_pid_entry(osnum, pid);
	if (!parent) {
		parent = get_pid_entry(osnum, pid);
		if (parent) {
			add_procfs_entries(parent, pid_entry_stuff,
					   cred->uid, cred->gid);
		}
	}
	_add_tid_entry(osnum, pid, tid, cred);
	up(&procfs_file_list_lock);
#endif
}

void
add_pid_entry(int osnum, int pid)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_add_pid_entry_body_result(
		osnum, pid, mcctrl_procfs_get_pid_cred_bridge,
		mcctrl_procfs_lock_bridge, mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_get_pid_entry_bridge,
		mcctrl_procfs_add_pid_entries_bridge,
		mcctrl_procfs_add_tid_with_cred_bridge);
#else
	struct procfs_list_entry *parent;
	const struct cred *cred = get_pid_cred(pid);

	if(!cred)
		return;
	down(&procfs_file_list_lock);
	parent = get_pid_entry(osnum, pid);
	add_procfs_entries(parent, pid_entry_stuff, cred->uid, cred->gid);
	_add_tid_entry(osnum, pid, pid, cred);
	up(&procfs_file_list_lock);
#endif
}

void
delete_tid_entry(int osnum, int pid, int tid)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_delete_tid_entry_body_result(
		osnum, pid, tid, mcctrl_procfs_lock_bridge,
		mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_find_tid_entry_bridge,
		mcctrl_procfs_delete_entry_bridge);
#else
	struct procfs_list_entry *e;

	down(&procfs_file_list_lock);
	e = find_tid_entry(osnum, pid, tid);
	if(e)
		delete_procfs_entries(e);
	up(&procfs_file_list_lock);
#endif
}

void
delete_pid_entry(int osnum, int pid)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_delete_pid_entry_body_result(
		osnum, pid, mcctrl_procfs_lock_bridge,
		mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_find_pid_entry_bridge,
		mcctrl_procfs_delete_entry_bridge);
#else
	struct procfs_list_entry *e;

	down(&procfs_file_list_lock);
	e = find_pid_entry(osnum, pid);
	if(e)
		delete_procfs_entries(e);
	up(&procfs_file_list_lock);
#endif
}

void
proc_exe_link(int osnum, int pid, const char *path)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_exe_link_body_result(
		osnum, pid, path, mcctrl_procfs_lock_bridge,
		mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_find_pid_entry_bridge,
		mcctrl_procfs_add_pid_exe_bridge,
		mcctrl_procfs_store_exe_path_bridge,
		mcctrl_procfs_add_task_exe_links_bridge);
#else
	struct procfs_list_entry *parent;
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	down(&procfs_file_list_lock);
	parent = find_pid_entry(osnum, pid);
	if(parent){
		struct procfs_list_entry *task;
		struct procfs_list_entry *e;

		e = add_procfs_entry(parent, "exe", S_IFLNK | 0777, uid, gid,
		                     path);
		if (!e)
			goto out;
		e->data = kmalloc(strlen(path) + 1, GFP_KERNEL);
		strcpy(e->data, path);
		task = find_procfs_entry(parent, "task");
		list_for_each_entry(parent, &task->children, list) {
			add_procfs_entry(parent, "exe", S_IFLNK | 0777,
			                 uid, gid, path);
		}
	}
out:
	up(&procfs_file_list_lock);
#endif
}

/**
 * \brief Initialization for procfs
 *
 * \param osnum os number
 */
void
procfs_init(int osnum)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_init_body_result(
		osnum, mcctrl_procfs_lock_bridge,
		mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_get_base_entry_bridge,
		mcctrl_procfs_add_base_entries_bridge);
#else
	struct procfs_list_entry *parent;
	kuid_t uid = KUIDT_INIT(0);
	kgid_t gid = KGIDT_INIT(0);

	down(&procfs_file_list_lock);
	parent = get_base_entry(osnum);
	add_procfs_entries(parent, base_entry_stuff, uid, gid);
	up(&procfs_file_list_lock);
#endif
}

/**
 * \brief Finalization for procfs
 *
 * \param osnum os number
 */
void
procfs_exit(int osnum)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_exit_body_result(
		osnum, mcctrl_procfs_lock_bridge,
		mcctrl_procfs_unlock_bridge,
		mcctrl_procfs_find_base_entry_bridge,
		mcctrl_procfs_delete_entry_bridge);
#else
	struct procfs_list_entry *e;

	down(&procfs_file_list_lock);
	e = find_base_entry(osnum);
	if (e) {
		delete_procfs_entries(e);
	}
	up(&procfs_file_list_lock);
#endif
}

#ifdef MCCTRL_RUST_HELPERS
static int mcctrl_procfs_entry_osnum_bridge(void *entry);
static const char *mcctrl_procfs_getpath_bridge(void *entry, char *buf,
						unsigned long size);
static void *mcctrl_procfs_os_lookup_bridge(int osnum);
static void *mcctrl_procfs_get_usrdata_bridge(void *os);
static void *mcctrl_procfs_get_per_proc_bridge(void *usrdata, int pid);
static void mcctrl_procfs_put_per_proc_bridge(void *ppd);
static int mcctrl_procfs_ppd_cpu_bridge(void *ppd);
static int mcctrl_procfs_get_order_bridge(unsigned long count);
static void *mcctrl_procfs_alloc_pages_bridge(int order);
static void mcctrl_procfs_free_pages_bridge(void *ptr, int order);
static unsigned long mcctrl_procfs_virt_to_phys_bridge(void *ptr);
static void *mcctrl_procfs_alloc_read_bridge(void);
static void mcctrl_procfs_init_read_write_read_bridge(void *opaque,
						      unsigned long pbuf,
						      long offset,
						      int count,
						      int read_write,
						      const char *path);
static int mcctrl_procfs_send_request_bridge(void *os, int cpu, int pid,
					     void *opaque, int *do_free);
static int mcctrl_procfs_read_ret_bridge(void *opaque);
static int mcctrl_procfs_read_eof_bridge(void *opaque);
static void mcctrl_procfs_free_bridge(void *ptr);
static int mcctrl_procfs_copy_kernel_to_user_bridge(void *ubuf, void *kbuf,
						    unsigned long size);
static void mcctrl_procfs_bad_osnum_bridge(void);
static void mcctrl_procfs_osnum_mismatch_bridge(int path_osnum,
						int entry_osnum);
static void mcctrl_procfs_no_os_bridge(int osnum);
static void mcctrl_procfs_no_usrdata_bridge(int osnum);
static void mcctrl_procfs_no_ppd_bridge(int pid);
static void mcctrl_procfs_alloc_error_bridge(void);
static void mcctrl_procfs_copy_error_bridge(void);
static void mcctrl_procfs_read_write_timeout_bridge(void);
#endif

/**
 * \brief The callback funciton for McKernel procfs
 *
 * This function conforms to the 2) way of fs/proc/generic.c
 * from linux-2.6.39.4.
 */
static ssize_t __mckernel_procfs_read_write(
		struct file *file,
		char __user *buf, size_t nbytes,
		loff_t *ppos, int read_write)
{
#ifdef MCCTRL_RUST_HELPERS
	char pathbuf[PROCFS_NAME_MAX];
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	struct inode *inode = file->f_inode;
	struct proc_dir_entry *dp = PDE(inode);
	struct procfs_list_entry *e = dp->data;
#else
	struct inode *inode = file->f_inode;
	struct procfs_list_entry *e = MCCTRL_PDE_DATA(inode);
#endif

	return mcctrl_procfs_read_write_body_result(
		e, (void *)buf, nbytes, (long *)ppos, read_write,
		pathbuf, PROCFS_NAME_MAX, PAGE_SIZE,
		mcctrl_procfs_entry_osnum_bridge,
		mcctrl_procfs_getpath_bridge,
		mcctrl_procfs_os_lookup_bridge,
		mcctrl_procfs_get_usrdata_bridge,
		mcctrl_procfs_get_per_proc_bridge,
		mcctrl_procfs_put_per_proc_bridge,
		mcctrl_procfs_ppd_cpu_bridge,
		mcctrl_procfs_get_order_bridge,
		mcctrl_procfs_alloc_pages_bridge,
		mcctrl_procfs_free_pages_bridge,
		mcctrl_procfs_virt_to_phys_bridge,
		mcctrl_procfs_alloc_read_bridge,
		mcctrl_procfs_init_read_write_read_bridge,
		mcctrl_procfs_send_request_bridge,
		mcctrl_procfs_read_ret_bridge,
		mcctrl_procfs_read_eof_bridge,
		mcctrl_procfs_free_bridge,
		mcctrl_procfs_copy_kernel_to_user_bridge,
		mcctrl_procfs_bad_osnum_bridge,
		mcctrl_procfs_osnum_mismatch_bridge,
		mcctrl_procfs_no_os_bridge,
		mcctrl_procfs_no_usrdata_bridge,
		mcctrl_procfs_no_ppd_bridge,
		mcctrl_procfs_alloc_error_bridge,
		mcctrl_procfs_copy_error_bridge,
		mcctrl_procfs_read_write_timeout_bridge);
#else
	struct inode * inode = file->f_inode;
	char *kern_buffer = NULL;
	int order = 0;
	volatile struct procfs_read *r = NULL;
	struct ikc_scd_packet isp;
	int ret, osnum, pid;
	unsigned long pbuf;
	size_t count = nbytes;
	size_t copy_size = 0;
	size_t copied = 0;
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	struct proc_dir_entry *dp = PDE(inode);
	struct procfs_list_entry *e = dp->data;
#else
	struct procfs_list_entry *e = MCCTRL_PDE_DATA(inode);
#endif
	loff_t offset = *ppos;
	char pathbuf[PROCFS_NAME_MAX];
	char *path, *p;
	ihk_os_t os = NULL;
	struct mcctrl_usrdata *udp = NULL;
	struct mcctrl_per_proc_data *ppd = NULL;

	if (count <= 0 || offset < 0) {
		return 0;
	}

	path = getpath(e, pathbuf, PROCFS_NAME_MAX);
	dprintk("%s: invoked for %s, offset: %lu, count: %lu\n",
			__FUNCTION__, path,
			(unsigned long)offset, count);

	/* Verify OS number */
	ret = sscanf(path, "mcos%d/", &osnum);
	if (ret != 1) {
		printk("%s: error: couldn't determine OS number\n", __FUNCTION__);
		return -EINVAL;
	}

	if (osnum != e->osnum) {
		printk("%s: error: OS numbers don't match\n", __FUNCTION__);
		return -EINVAL;
	}

	/* Is this request for a specific process? */
	p = strchr(path, '/') + 1;
	ret = sscanf(p, "%d/", &pid);
	if (ret != 1) {
		pid = -1;
	}

	os = osnum_to_os(osnum);
	if (!os) {
		printk("%s: error: no IHK OS data found for OS %d\n",
				__FUNCTION__, osnum);
		return -EINVAL;
	}

	udp = ihk_host_os_get_usrdata(os);
	if (!udp) {
		printk("%s: error: no MCCTRL data found for OS %d\n",
				__FUNCTION__, osnum);
		return -EINVAL;
	}

	if (pid > 0) {
		ppd = mcctrl_get_per_proc_data(udp, pid);

		if (unlikely(!ppd)) {
			printk("%s: error: no per-process structure for PID %d",
					__FUNCTION__, pid);
			return -EINVAL;
		}
	}

	/* NOTE: we need physically contigous memory to pass through IKC */
	for (order = get_order(count); order >= 0; order--) {
		kern_buffer = (char *)__get_free_pages(GFP_KERNEL, order);
		if (kern_buffer) {
			break;
		}
	}

	if (!kern_buffer) {
		printk("%s: ERROR: allocating kernel buffer\n", __FUNCTION__);
		ret = -ENOMEM;
		goto out;
	}
	copy_size = PAGE_SIZE * (1 << order);

	pbuf = virt_to_phys(kern_buffer);

	r = kmalloc(sizeof(struct procfs_read), GFP_KERNEL);
	if (r == NULL) {
		ret = -ENOMEM;
		goto out;
	}

	while (count > 0) {
		int this_len = min_t(ssize_t, count, copy_size);
		int do_free;

		r->pbuf = pbuf;
		r->eof = 0;
		r->ret = -EIO; /* default */
		r->offset = offset;
		r->count = this_len;
		r->readwrite = read_write;
		strncpy((char *)r->fname, path, PROCFS_NAME_MAX);
		isp.msg = SCD_MSG_PROCFS_REQUEST;
		isp.ref = 0;
		isp.arg = virt_to_phys(r);
		isp.pid = pid;

		ret = mcctrl_ikc_send_wait(osnum_to_os(e->osnum),
					   (pid > 0) ? ppd->ikc_target_cpu : 0,
					   &isp, 5000, NULL, &do_free, 1, r);

		if (!do_free && ret >= 0) {
			ret = -EIO;
		}

		if (ret < 0) {
			if (ret == -ETIME) {
				pr_info("%s: error: timeout (1 sec)\n",
				       __func__);
			}
			else if (ret == -ERESTARTSYS) {
				ret = -ERESTART;
			}
			if (!do_free)
				r = NULL;
			goto out;
		}

		/* Wake up and check the result. */
		dprintk("%s: woke up. ret: %d, eof: %d\n",
				__FUNCTION__, r->ret, r->eof);

		if (r->ret > 0) {
			if (read_write == 0) {
				if (copy_to_user(buf, kern_buffer, r->ret)) {
					printk("%s: ERROR: copy_to_user failed.\n", __FUNCTION__);
					ret = -EFAULT;
					goto out;
				}
			}

			buf += r->ret;
			offset += r->ret;
			copied += r->ret;
			count -= r->ret;
		}
		else {
			if (!copied) {
				/* Transmit error from McKernel */
				copied = r->ret;
			}
			break;
		}

		if (r->eof != 0) {
			break;
		}
	}
	*ppos = offset;
	ret = copied;

out:
	if (ppd)
		mcctrl_put_per_proc_data(ppd);
	if (kern_buffer)
		free_pages((uintptr_t)kern_buffer, order);
	if (r)
		kfree((void *)r);

	return ret;
#endif
}

static ssize_t mckernel_procfs_read(struct file *file,
		char __user *buf, size_t nbytes, loff_t *ppos)
{
	return __mckernel_procfs_read_write(file, buf, nbytes, ppos, 0);
}

static ssize_t mckernel_procfs_write(struct file *file,
		const char __user *buf, size_t nbytes, loff_t *ppos)
{
	return __mckernel_procfs_read_write(file,
			(char __user *)buf, nbytes, ppos, 1);
}

static loff_t
mckernel_procfs_lseek(struct file *file, loff_t offset, int orig)
{
#ifdef MCCTRL_RUST_HELPERS
	long new_pos = file->f_pos;
	long ret = mcctrl_procfs_lseek_body_result(file->f_pos, offset, orig,
						   &new_pos);

	if (orig == 0 || orig == 1)
		file->f_pos = new_pos;
	return ret;
#else
	switch (orig) {
	case 0:
		file->f_pos = offset;
		break;
	case 1:
		file->f_pos += offset;
		break;
	default:
		return -EINVAL;
	}
	return file->f_pos;
#endif
}

struct procfs_work {
	void *os;
	int msg;
	int pid;
	unsigned long arg;
	unsigned long resp_pa;
	struct work_struct work;
};

#ifdef MCCTRL_RUST_HELPERS
static void procfsm_work_main(struct work_struct *work0);

static void *mcctrl_procfs_work_alloc_bridge(unsigned long size)
{
	return kzalloc(size, GFP_ATOMIC);
}

static void mcctrl_procfs_work_init_schedule_bridge(void *opaque)
{
	struct procfs_work *work = opaque;

	INIT_WORK(&work->work, &procfsm_work_main);
	schedule_work(&work->work);
}

static void mcctrl_procfs_alloc_failed_bridge(void)
{
	printk("%s: kzalloc failed\n", "procfsm_packet_handler");
}

static int mcctrl_procfs_get_index_bridge(void *os)
{
	return ihk_host_os_get_index(os);
}

static void mcctrl_procfs_add_tid_entry_bridge(int osnum, int pid, int tid)
{
	add_tid_entry(osnum, pid, tid);
}

static void mcctrl_procfs_delete_tid_entry_bridge(int osnum, int pid, int tid)
{
	delete_tid_entry(osnum, pid, tid);
}

static void *mcctrl_procfs_os_to_dev_bridge(void *os)
{
	return ihk_os_to_dev(os);
}

static unsigned long mcctrl_procfs_map_memory_bridge(void *dev,
						    unsigned long phys,
						    unsigned long size)
{
	return ihk_device_map_memory(dev, phys, size);
}

static void *mcctrl_procfs_map_virtual_bridge(void *dev, unsigned long phys,
					     unsigned long size, void *attr,
					     int flags)
{
	return ihk_device_map_virtual(dev, phys, size, attr, flags);
}

static void mcctrl_procfs_unmap_virtual_bridge(void *dev, void *virt,
					       unsigned long size)
{
	ihk_device_unmap_virtual(dev, virt, size);
}

static void mcctrl_procfs_unmap_memory_bridge(void *dev, unsigned long phys,
					      unsigned long size)
{
	ihk_device_unmap_memory(dev, phys, size);
}

static void mcctrl_procfs_unknown_work_bridge(int msg, int pid,
					     unsigned long arg)
{
	pr_warn("%s: unknown work: msg: %d, pid: %d, arg: %lu)\n",
		"procfsm_work_main", msg, pid, arg);
}

static void mcctrl_procfs_work_free_bridge(void *work)
{
	kfree(work);
}
#endif

static void procfsm_work_main(struct work_struct *work0)
{
	struct procfs_work *work = container_of(work0, struct procfs_work, work);
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_procfs_work_main_body_result(work, sizeof(int),
					    mcctrl_procfs_get_index_bridge,
					    mcctrl_procfs_add_tid_entry_bridge,
					    mcctrl_procfs_delete_tid_entry_bridge,
					    mcctrl_procfs_os_to_dev_bridge,
					    mcctrl_procfs_map_memory_bridge,
					    mcctrl_procfs_map_virtual_bridge,
					    mcctrl_procfs_unmap_virtual_bridge,
					    mcctrl_procfs_unmap_memory_bridge,
					    mcctrl_procfs_unknown_work_bridge,
					    mcctrl_procfs_work_free_bridge);
#else
	unsigned long phys;
	int *done;

	switch (work->msg) {
	case SCD_MSG_PROCFS_TID_CREATE:
		add_tid_entry(ihk_host_os_get_index(work->os),
				work->pid, work->arg);
		phys = ihk_device_map_memory(ihk_os_to_dev(work->os),
					     work->resp_pa, sizeof(int));
		done = ihk_device_map_virtual(ihk_os_to_dev(work->os),
					      phys, sizeof(int), NULL, 0);
		*done = 1;
		ihk_device_unmap_virtual(ihk_os_to_dev(work->os),
						 done, sizeof(int));
		ihk_device_unmap_memory(ihk_os_to_dev(work->os),
					phys, sizeof(int));
		break;

	case SCD_MSG_PROCFS_TID_DELETE:
		delete_tid_entry(ihk_host_os_get_index(work->os),
				 work->pid, work->arg);
		break;

	default:
		pr_warn("%s: unknown work: msg: %d, pid: %d, arg: %lu)\n",
			__func__, work->msg, work->pid, work->arg);
		break;
	}

	kfree(work);
	return;
#endif
}

int procfsm_packet_handler(void *os, int msg, int pid, unsigned long arg,
			   unsigned long resp_pa)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_packet_handler_body_result(
		os, msg, pid, arg, resp_pa, sizeof(struct procfs_work),
		mcctrl_procfs_work_alloc_bridge,
		mcctrl_procfs_work_init_schedule_bridge,
		mcctrl_procfs_alloc_failed_bridge);
#else
	struct procfs_work *work = NULL;

	work = kzalloc(sizeof(*work), GFP_ATOMIC);
	if (!work) {
		printk("%s: kzalloc failed\n", __FUNCTION__);
		return -1;
	}

	work->os = os;
	work->msg = msg;
	work->pid = pid;
	work->arg = arg;
	work->resp_pa = resp_pa;
	INIT_WORK(&work->work, &procfsm_work_main);

	schedule_work(&work->work);
	return 0;
#endif
}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
static const struct proc_ops mckernel_forward_ro = {
	.proc_lseek	= mckernel_procfs_lseek,
	.proc_read	= mckernel_procfs_read,
	.proc_write	= NULL,
};

static const struct proc_ops mckernel_forward = {
	.proc_lseek	= mckernel_procfs_lseek,
	.proc_read	= mckernel_procfs_read,
	.proc_write	= mckernel_procfs_write,
};
#else
static const struct file_operations mckernel_forward_ro = {
	.llseek		= mckernel_procfs_lseek,
	.read		= mckernel_procfs_read,
	.write		= NULL,
};

static const struct file_operations mckernel_forward = {
	.llseek		= mckernel_procfs_lseek,
	.read		= mckernel_procfs_read,
	.write		= mckernel_procfs_write,
};
#endif

#define PA_NULL (-1L)

struct mckernel_procfs_buffer_info {
	unsigned long top_pa;
	unsigned long cur_pa;
	ihk_os_t os;
	int pid;
	char path[];
};

struct mckernel_procfs_buffer {
	unsigned long next_pa;
	unsigned long pos;
	unsigned long size;
	char buf[];
};

#ifdef MCCTRL_RUST_HELPERS
static int mcctrl_procfs_entry_osnum_bridge(void *entry)
{
	return ((struct procfs_list_entry *)entry)->osnum;
}

static void *mcctrl_procfs_os_lookup_bridge(int osnum)
{
	return osnum_to_os(osnum);
}

static void *mcctrl_procfs_alloc_bridge(unsigned long size)
{
	return kmalloc(size, GFP_KERNEL);
}

static void mcctrl_procfs_free_bridge(void *ptr)
{
	kfree(ptr);
}

static const char *mcctrl_procfs_getpath_bridge(void *entry, char *buf,
						unsigned long size)
{
	return getpath(entry, buf, size);
}

static void mcctrl_procfs_init_buffer_info_bridge(void *opaque, void *os,
						  int pid,
						  unsigned long pa_null,
						  const char *path)
{
	struct mckernel_procfs_buffer_info *info = opaque;

	info->top_pa = pa_null;
	info->cur_pa = pa_null;
	info->os = os;
	info->pid = pid;
	strcpy(info->path, path);
}

static void mcctrl_procfs_set_file_private_bridge(void *file, void *data)
{
	((struct file *)file)->private_data = data;
}

static void *mcctrl_procfs_get_file_private_bridge(void *file)
{
	return ((struct file *)file)->private_data;
}

static unsigned long mcctrl_procfs_info_top_pa_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer_info *)opaque)->top_pa;
}

static void *mcctrl_procfs_info_os_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer_info *)opaque)->os;
}

static void *mcctrl_procfs_alloc_read_bridge(void)
{
	return kmalloc(sizeof(struct procfs_read), GFP_KERNEL);
}

static void mcctrl_procfs_init_release_read_bridge(void *opaque,
						  unsigned long top_pa)
{
	volatile struct procfs_read *r = opaque;

	memset((void *)r, '\0', sizeof(struct procfs_read));
	r->pbuf = top_pa;
	r->ret = -EIO;
	r->fname[0] = '\0';
}

static int mcctrl_procfs_send_release_bridge(void *os, void *opaque,
					     int *do_free)
{
	struct ikc_scd_packet isp;
	volatile struct procfs_read *r = opaque;

	isp.msg = SCD_MSG_PROCFS_RELEASE;
	isp.ref = 0;
	isp.arg = virt_to_phys((void *)r);
	isp.pid = 0;
	return mcctrl_ikc_send_wait(os, 0, &isp, 5000, NULL, do_free, 1,
				    (void *)r);
}

static int mcctrl_procfs_read_ret_bridge(void *opaque)
{
	return ((volatile struct procfs_read *)opaque)->ret;
}

static void mcctrl_procfs_release_timeout_bridge(void)
{
	pr_info("%s: error: timeout (1 sec)\n",
		"mckernel_procfs_buff_release");
}

static int mcctrl_procfs_info_pid_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer_info *)opaque)->pid;
}

static unsigned long mcctrl_procfs_info_cur_pa_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer_info *)opaque)->cur_pa;
}

static const char *mcctrl_procfs_info_path_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer_info *)opaque)->path;
}

static void mcctrl_procfs_info_set_top_cur_bridge(void *opaque,
						  unsigned long top_pa,
						  unsigned long cur_pa)
{
	struct mckernel_procfs_buffer_info *info = opaque;

	info->top_pa = top_pa;
	info->cur_pa = cur_pa;
}

static void mcctrl_procfs_info_set_cur_bridge(void *opaque,
					      unsigned long cur_pa)
{
	((struct mckernel_procfs_buffer_info *)opaque)->cur_pa = cur_pa;
}

static void *mcctrl_procfs_get_usrdata_bridge(void *os)
{
	return ihk_host_os_get_usrdata(os);
}

static void *mcctrl_procfs_get_per_proc_bridge(void *usrdata, int pid)
{
	return mcctrl_get_per_proc_data(usrdata, pid);
}

static void mcctrl_procfs_put_per_proc_bridge(void *ppd)
{
	mcctrl_put_per_proc_data(ppd);
}

static int mcctrl_procfs_ppd_cpu_bridge(void *ppd)
{
	return ((struct mcctrl_per_proc_data *)ppd)->ikc_target_cpu;
}

static void mcctrl_procfs_init_request_read_bridge(void *opaque,
						   unsigned long pbuf,
						   const char *path)
{
	volatile struct procfs_read *r = opaque;

	memset((void *)r, '\0', sizeof(struct procfs_read));
	r->pbuf = pbuf;
	r->ret = -EIO;
	strncpy((char *)r->fname, path, PROCFS_NAME_MAX);
}

static int mcctrl_procfs_send_request_bridge(void *os, int cpu, int pid,
					     void *opaque, int *do_free)
{
	struct ikc_scd_packet isp;
	volatile struct procfs_read *r = opaque;

	isp.msg = SCD_MSG_PROCFS_REQUEST;
	isp.ref = 0;
	isp.arg = virt_to_phys((void *)r);
	isp.pid = pid;
	return mcctrl_ikc_send_wait(os, cpu, &isp, 5000, NULL, do_free, 1,
				    (void *)r);
}

static unsigned long mcctrl_procfs_read_pbuf_bridge(void *opaque)
{
	return ((volatile struct procfs_read *)opaque)->pbuf;
}

static unsigned long mcctrl_procfs_buffer_pos_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer *)opaque)->pos;
}

static unsigned long mcctrl_procfs_buffer_size_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer *)opaque)->size;
}

static unsigned long mcctrl_procfs_buffer_next_pa_bridge(void *opaque)
{
	return ((struct mckernel_procfs_buffer *)opaque)->next_pa;
}

static int mcctrl_procfs_copy_buffer_to_user_bridge(void *ubuf, void *opaque,
						    unsigned long offset,
						    unsigned long size)
{
	struct mckernel_procfs_buffer *buf = opaque;

	return copy_to_user((char __user *)ubuf, buf->buf + offset, size);
}

static void mcctrl_procfs_buff_read_no_usrdata_bridge(void)
{
	pr_err("%s: no MCCTRL data found for OS\n",
	       "mckernel_procfs_buff_read");
}

static void mcctrl_procfs_buff_read_no_ppd_bridge(int pid)
{
	pr_err("%s: no per-process structure for PID %d",
	       "mckernel_procfs_buff_read", pid);
}

static void mcctrl_procfs_buff_read_timeout_bridge(void)
{
	pr_info("%s: error: timeout (1 sec)\n",
		"mckernel_procfs_buff_read");
}

static int mcctrl_procfs_get_order_bridge(unsigned long count)
{
	return get_order(count);
}

static void *mcctrl_procfs_alloc_pages_bridge(int order)
{
	return (void *)__get_free_pages(GFP_KERNEL, order);
}

static void mcctrl_procfs_free_pages_bridge(void *ptr, int order)
{
	free_pages((uintptr_t)ptr, order);
}

static unsigned long mcctrl_procfs_virt_to_phys_bridge(void *ptr)
{
	return virt_to_phys(ptr);
}

static void mcctrl_procfs_init_read_write_read_bridge(void *opaque,
						      unsigned long pbuf,
						      long offset,
						      int count,
						      int read_write,
						      const char *path)
{
	volatile struct procfs_read *r = opaque;

	r->pbuf = pbuf;
	r->eof = 0;
	r->ret = -EIO;
	r->offset = offset;
	r->count = count;
	r->readwrite = read_write;
	strncpy((char *)r->fname, path, PROCFS_NAME_MAX);
}

static int mcctrl_procfs_read_eof_bridge(void *opaque)
{
	return ((volatile struct procfs_read *)opaque)->eof;
}

static int mcctrl_procfs_copy_kernel_to_user_bridge(void *ubuf, void *kbuf,
						    unsigned long size)
{
	return copy_to_user((char __user *)ubuf, kbuf, size);
}

static void mcctrl_procfs_bad_osnum_bridge(void)
{
	printk("%s: error: couldn't determine OS number\n",
	       "__mckernel_procfs_read_write");
}

static void mcctrl_procfs_osnum_mismatch_bridge(int path_osnum,
						int entry_osnum)
{
	printk("%s: error: OS numbers don't match (%d != %d)\n",
	       "__mckernel_procfs_read_write", path_osnum, entry_osnum);
}

static void mcctrl_procfs_no_os_bridge(int osnum)
{
	printk("%s: error: no IHK OS data found for OS %d\n",
	       "__mckernel_procfs_read_write", osnum);
}

static void mcctrl_procfs_no_usrdata_bridge(int osnum)
{
	printk("%s: error: no MCCTRL data found for OS %d\n",
	       "__mckernel_procfs_read_write", osnum);
}

static void mcctrl_procfs_no_ppd_bridge(int pid)
{
	printk("%s: error: no per-process structure for PID %d",
	       "__mckernel_procfs_read_write", pid);
}

static void mcctrl_procfs_alloc_error_bridge(void)
{
	printk("%s: ERROR: allocating kernel buffer\n",
	       "__mckernel_procfs_read_write");
}

static void mcctrl_procfs_copy_error_bridge(void)
{
	printk("%s: ERROR: copy_to_user failed.\n",
	       "__mckernel_procfs_read_write");
}

static void mcctrl_procfs_read_write_timeout_bridge(void)
{
	pr_info("%s: error: timeout (1 sec)\n",
		"__mckernel_procfs_read_write");
}
#endif

static int mckernel_procfs_buff_open(struct inode *inode, struct file *file)
{
#ifdef MCCTRL_RUST_HELPERS
#if LINUX_VERSION_CODE < KERNEL_VERSION(3, 10, 0)
	struct proc_dir_entry *dp = PDE(inode);
	struct procfs_list_entry *e = dp->data;
#else
	struct procfs_list_entry *e = MCCTRL_PDE_DATA(inode);
#endif
	return mcctrl_procfs_buff_open_body_result(
		e, file, PROCFS_NAME_MAX,
		sizeof(struct mckernel_procfs_buffer_info), PA_NULL,
		mcctrl_procfs_entry_osnum_bridge,
		mcctrl_procfs_os_lookup_bridge,
		mcctrl_procfs_alloc_bridge,
		mcctrl_procfs_free_bridge,
		mcctrl_procfs_getpath_bridge,
		mcctrl_procfs_init_buffer_info_bridge,
		mcctrl_procfs_set_file_private_bridge);
#else
	struct mckernel_procfs_buffer_info *info;
	int pid;
	int ret;
	char *path;
	char *path_buf;
	char *p;
	ihk_os_t os;
#if LINUX_VERSION_CODE < KERNEL_VERSION(3, 10, 0)
	struct proc_dir_entry *dp = PDE(inode);
	struct procfs_list_entry *e = dp->data;
#else
	struct procfs_list_entry *e = MCCTRL_PDE_DATA(inode);
#endif

	os = osnum_to_os(e->osnum);
	if (!os) {
		return -EINVAL;
	}
	path_buf = kmalloc(PROCFS_NAME_MAX, GFP_KERNEL);
	if (!path_buf) {
		return -ENOMEM;
	}
	path = getpath(e, path_buf, PROCFS_NAME_MAX);
	p = strchr(path, '/') + 1;
	ret = sscanf(p, "%d/", &pid);
	if (ret != 1) {
		pid = -1;
	}

	info = kmalloc(sizeof(struct mckernel_procfs_buffer_info) +
		       strlen(path) + 1, GFP_KERNEL);
	if (!info) {
		kfree(path_buf);
		return -ENOMEM;
	}
	info->top_pa = PA_NULL;
	info->cur_pa = PA_NULL;
	info->os = os;
	info->pid = pid;
	strcpy(info->path, path);
	file->private_data = info;

	kfree(path_buf);
	return 0;
#endif
}

static int mckernel_procfs_buff_release(struct inode *inode, struct file *file)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_buff_release_body_result(
		file, PA_NULL, mcctrl_procfs_get_file_private_bridge,
		mcctrl_procfs_set_file_private_bridge,
		mcctrl_procfs_info_top_pa_bridge,
		mcctrl_procfs_info_os_bridge,
		mcctrl_procfs_alloc_read_bridge,
		mcctrl_procfs_init_release_read_bridge,
		mcctrl_procfs_send_release_bridge,
		mcctrl_procfs_read_ret_bridge,
		mcctrl_procfs_free_bridge,
		mcctrl_procfs_release_timeout_bridge);
#else
	struct mckernel_procfs_buffer_info *info = file->private_data;
	int rc = 0;

	if (!info) {
		return -EIO;
	}

	file->private_data = NULL;
	if (info->top_pa != PA_NULL) {
		int ret;
		struct procfs_read *r = NULL;
		struct ikc_scd_packet isp;
		int do_free;

		r = kmalloc(sizeof(struct procfs_read), GFP_KERNEL);
		if (r == NULL) {
			rc = -ENOMEM;
			goto out;
		}
		memset(r, '\0', sizeof(struct procfs_read));
		r->pbuf = info->top_pa;
		r->ret = -EIO; /* default */
		r->fname[0] = '\0';
		isp.msg = SCD_MSG_PROCFS_RELEASE;
		isp.ref = 0;
		isp.arg = virt_to_phys(r);
		isp.pid = 0;

		rc = -EIO;
		ret = mcctrl_ikc_send_wait(info->os, 0,
					   &isp, 5000, NULL, &do_free, 1, r);

		if (!do_free && ret >= 0) {
			ret = -EIO;
		}

		if (ret < 0) {
			rc = ret;
			if (ret == -ETIME) {
				pr_info("%s: error: timeout (1 sec)\n",
				       __func__);
			}
			else if (ret == -ERESTARTSYS) {
				rc = -ERESTART;
			}
			if (!do_free)
				r = NULL;
			goto out;
		}

		if (r->ret < 0) {
			rc = r->ret;
			goto out;
		}
		rc = 0;
out:
		if (r)
			kfree((void *)r);
	}
	kfree(info);
	return rc;
#endif
}

static ssize_t mckernel_procfs_buff_read(struct file *file, char __user *ubuf,
					 size_t nbytes, loff_t *ppos)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_procfs_buff_read_body_result(
		file, (void *)ubuf, nbytes, (long *)ppos, PA_NULL, PAGE_SIZE,
		mcctrl_procfs_get_file_private_bridge,
		mcctrl_procfs_info_os_bridge,
		mcctrl_procfs_info_pid_bridge,
		mcctrl_procfs_info_top_pa_bridge,
		mcctrl_procfs_info_cur_pa_bridge,
		mcctrl_procfs_info_path_bridge,
		mcctrl_procfs_info_set_top_cur_bridge,
		mcctrl_procfs_info_set_cur_bridge,
		mcctrl_procfs_get_usrdata_bridge,
		mcctrl_procfs_get_per_proc_bridge,
		mcctrl_procfs_put_per_proc_bridge,
		mcctrl_procfs_ppd_cpu_bridge,
		mcctrl_procfs_alloc_read_bridge,
		mcctrl_procfs_init_request_read_bridge,
		mcctrl_procfs_send_request_bridge,
		mcctrl_procfs_read_ret_bridge,
		mcctrl_procfs_read_pbuf_bridge,
		mcctrl_procfs_free_bridge,
		mcctrl_procfs_os_to_dev_bridge,
		mcctrl_procfs_map_memory_bridge,
		mcctrl_procfs_map_virtual_bridge,
		mcctrl_procfs_unmap_virtual_bridge,
		mcctrl_procfs_unmap_memory_bridge,
		mcctrl_procfs_buffer_pos_bridge,
		mcctrl_procfs_buffer_size_bridge,
		mcctrl_procfs_buffer_next_pa_bridge,
		mcctrl_procfs_copy_buffer_to_user_bridge,
		mcctrl_procfs_buff_read_no_usrdata_bridge,
		mcctrl_procfs_buff_read_no_ppd_bridge,
		mcctrl_procfs_buff_read_timeout_bridge);
#else
	struct mckernel_procfs_buffer_info *info = file->private_data;
	unsigned long phys;
	struct mckernel_procfs_buffer *buf;
	int pos = *ppos;
	ssize_t l = 0;
	int done = 0;
	ihk_os_t os;

	if (nbytes <= 0 || *ppos < 0) {
		return 0;
	}

	if (!info) {
		return -EIO;
	}

	os = info->os;
	if (info->top_pa == PA_NULL) {
		int ret;
		int pid = info->pid;
		struct procfs_read *r = NULL;
		struct ikc_scd_packet isp;
		struct mcctrl_usrdata *udp = NULL;
		struct mcctrl_per_proc_data *ppd = NULL;
		int do_free;

		udp = ihk_host_os_get_usrdata(os);
		if (!udp) {
			pr_err("%s: no MCCTRL data found for OS\n",
					__func__);
			return -EINVAL;
		}

		if (pid > 0) {
			ppd = mcctrl_get_per_proc_data(udp, pid);

			if (unlikely(!ppd)) {
				pr_err("%s: no per-process structure for PID %d",
						__func__, pid);
				return -EINVAL;
			}
		}

		r = kmalloc(sizeof(struct procfs_read), GFP_KERNEL);
		if (r == NULL) {
			l = -ENOMEM;
			done = 1;
			goto out;
		}
		memset(r, '\0', sizeof(struct procfs_read));
		r->pbuf = PA_NULL;
		r->ret = -EIO; /* default */
		strncpy((char *)r->fname, info->path, PROCFS_NAME_MAX);
		isp.msg = SCD_MSG_PROCFS_REQUEST;
		isp.ref = 0;
		isp.arg = virt_to_phys(r);
		isp.pid = pid;

		l = -EIO;
		done = 1;
		ret = mcctrl_ikc_send_wait(os,
					   (pid > 0) ? ppd->ikc_target_cpu : 0,
					   &isp, 5000, NULL, &do_free, 1, r);

		if (!do_free && ret >= 0) {
			ret = -EIO;
		}

		if (ret < 0) {
			l = ret;
			if (ret == -ETIME) {
				pr_info("%s: error: timeout (1 sec)\n",
				       __func__);
			}
			else if (ret == -ERESTARTSYS) {
				l = -ERESTART;
			}
			if (!do_free)
				r = NULL;
			goto out;
		}

		if (r->ret < 0) {
			l = r->ret;
			goto out;
		}

		done = 0;
		l = 0;
		info->top_pa = info->cur_pa = r->pbuf;

out:
		if (ppd)
			mcctrl_put_per_proc_data(ppd);
		if (r)
			kfree((void *)r);
	}

	if (info->cur_pa == PA_NULL) {
		info->cur_pa = info->top_pa;
	}

	while (!done && info->cur_pa != PA_NULL) {
		long bpos;
		long bsize;

		phys = ihk_device_map_memory(ihk_os_to_dev(os), info->cur_pa,
					     PAGE_SIZE);
#ifdef CONFIG_MIC
		buf = ioremap_wc(phys, PAGE_SIZE);
#else
		buf = ihk_device_map_virtual(ihk_os_to_dev(os), phys,
					     PAGE_SIZE, NULL, 0);
#endif

		if (pos < buf->pos) {
			info->cur_pa = info->top_pa;
			goto rep;
		}

		if (pos >= buf->pos + buf->size) {
			info->cur_pa = buf->next_pa;
			goto rep;
		}

		bpos = pos - buf->pos;
		bsize = (buf->pos + buf->size) - pos;
		if (bsize > (nbytes - l)) {
			bsize = nbytes - l;
		}
		if (copy_to_user(ubuf, buf->buf + bpos, bsize)) {
			done = 1;
			pos = *ppos;
			l = -EFAULT;
		}
		else {
			ubuf += bsize;
			pos += bsize;
			l += bsize;
			if (l == nbytes) {
				done = 1;
			}
		}
rep:
#ifdef CONFIG_MIC
		iounmap(buf);
#else
		ihk_device_unmap_virtual(ihk_os_to_dev(os), buf, PAGE_SIZE);
#endif
		ihk_device_unmap_memory(ihk_os_to_dev(os), phys, PAGE_SIZE);
	};

	*ppos = pos;
	return l;
#endif
}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
static const struct proc_ops mckernel_buff_io = {
	.proc_lseek	= mckernel_procfs_lseek,
	.proc_read	= mckernel_procfs_buff_read,
	.proc_write	= NULL,
	.proc_open	= mckernel_procfs_buff_open,
	.proc_release	= mckernel_procfs_buff_release,
};
#else
static const struct file_operations mckernel_buff_io = {
	.llseek		= mckernel_procfs_lseek,
	.read		= mckernel_procfs_buff_read,
	.write		= NULL,
	.open		= mckernel_procfs_buff_open,
	.release	= mckernel_procfs_buff_release,
};
#endif

static const struct procfs_entry tid_entry_stuff[] = {
//	PROC_REG("auxv",       S_IRUSR, NULL),
//	PROC_REG("clear_refs", S_IWUSR, NULL),
//	PROC_REG("cmdline",    S_IRUGO, NULL),
//	PROC_REG("comm",       S_IRUGO|S_IWUSR, NULL),
//	PROC_REG("environ",    S_IRUSR, NULL),
//	PROC_LNK("exe",        mckernel_readlink),
//	PROC_REG("limits",     S_IRUSR|S_IWUSR, NULL),
//	PROC_REG("maps",       S_IRUGO, NULL),
	PROC_REG("mem",        0600, NULL),
//	PROC_REG("pagemap",    S_IRUGO, NULL),
//	PROC_REG("smaps",      S_IRUGO, NULL),
	PROC_REG("stat",       0444, &mckernel_buff_io),
//	PROC_REG("statm",      S_IRUGO, NULL),
//	PROC_REG("status",     S_IRUGO, NULL),
//	PROC_REG("syscall",    S_IRUGO, NULL),
//	PROC_REG("wchan",      S_IRUGO, NULL),
	PROC_TERM
};

static const struct procfs_entry pid_entry_stuff[] = {
	PROC_REG("auxv",       0400, &mckernel_buff_io),
	/* Support the case where McKernel process retrieves its job-id under the Fujitsu TCS suite. */
//	PROC_REG("cgroup",     S_IXUSR, NULL),
//	PROC_REG("clear_refs", S_IWUSR, NULL),
	PROC_REG("cmdline",    0444, &mckernel_buff_io),
	PROC_REG("comm",       0644, &mckernel_buff_io),
//	PROC_REG("coredump_filter", S_IRUGO|S_IWUSR, NULL),
//	PROC_REG("cpuset",     S_IRUGO, NULL),
//	PROC_REG("environ",    S_IRUSR, NULL),
//	PROC_LNK("exe",        mckernel_readlink),
//	PROC_REG("limits",     S_IRUSR|S_IWUSR, NULL),
	PROC_REG("maps",       0444, &mckernel_buff_io),
	PROC_REG("mem",        0600, NULL),
	PROC_REG("pagemap",    0444, NULL),
//	PROC_REG("smaps",      S_IRUGO, NULL),
	PROC_REG("stat",       0444, &mckernel_buff_io),
//	PROC_REG("statm",      S_IRUGO, NULL),
	PROC_REG("status",     0444, &mckernel_buff_io),
//	PROC_REG("syscall",    S_IRUGO, NULL),
	PROC_DIR("task",       0555),
//	PROC_REG("wchan",      S_IRUGO, NULL),
	PROC_TERM
};

static const struct procfs_entry base_entry_stuff[] = {
//	PROC_REG("cmdline",    S_IRUGO, NULL),
#ifdef POSTK_DEBUG_ARCH_DEP_42 /* /proc/cpuinfo support added. */
	PROC_REG("cpuinfo",    0444, &mckernel_buff_io),
#else /* POSTK_DEBUG_ARCH_DEP_42 */
//	PROC_REG("cpuinfo",    S_IRUGO, NULL),
#endif /* POSTK_DEBUG_ARCH_DEP_42 */
//	PROC_REG("meminfo",    S_IRUGO, NULL),
//	PROC_REG("pagetypeinfo",S_IRUGO, NULL),
//	PROC_REG("softirq",    S_IRUGO, NULL),
	PROC_REG("stat",       0444, &mckernel_buff_io),
//	PROC_REG("uptime",     S_IRUGO, NULL),
//	PROC_REG("version",    S_IRUGO, NULL),
//	PROC_REG("vmallocinfo",S_IRUSR, NULL),
//	PROC_REG("vmstat",     S_IRUGO, NULL),
//	PROC_REG("zoneinfo",   S_IRUGO, NULL),
	PROC_REG("mckernel",   S_IRUGO, &mckernel_buff_io),
	PROC_TERM
};
