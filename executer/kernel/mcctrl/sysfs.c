/**
 * \file sysfs.c
 *  License details are found in the file LICENSE.
 * \brief
 *  sysfs framework, IHK-Master side
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2015 - 2016  RIKEN AICS
 */
/*
 * HISTORY:
 */

#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/device.h>
#include <linux/version.h>
#include <linux/interrupt.h>
#include "mcctrl.h"
#include "mcctrl_rust.h"
#include "sysfs_msg.h"

#define dprintk(...) do { if (0) printk(__VA_ARGS__); } while (0)
#define wprintk(...) do { if (1) printk(KERN_WARNING __VA_ARGS__); } while (0)
#define eprintk(...) do { if (1) printk(KERN_ERR __VA_ARGS__); } while (0)

#ifndef MCCTRL_RUST_HELPERS
int
is_special_sysfs_ops(void *ops)
{
	return (((long)SYSFS_SPECIAL_OPS_MIN <= (long)ops)
			&& ((long)ops <= (long)SYSFS_SPECIAL_OPS_MAX));
}
#endif

#ifndef MCCTRL_RUST_HELPERS
static int
mcctrl_sysfs_inited_result(unsigned long sysfs_buf)
{
	return !!sysfs_buf;
}
#endif

enum {
	/* sysfsm_node.type */
	SNT_FILE = 1,
	SNT_DIR = 2,
	SNT_LINK = 3,
};

struct sysfsm_node {
	int8_t type;
	int8_t padding[7];
	char *name;
	struct sysfsm_node *parent;
	struct sysfsm_data *sdp;
	struct list_head chain;
	union {
		/* SNT_DIR */
		struct {
			struct kobject kobj;
			struct list_head children;
		};

		/* SNT_FILE */
		struct {
			struct attribute attr;
			struct sysfsm_ops *server_ops;
			long client_ops;
			long client_instance;
		};
	};
}; /* struct sysfsm_node */

struct sysfs_work {
	void *os;
	int msg;
	int err;
	long arg1;
	long arg2;
	struct work_struct work;
}; /* struct sysfs_work */

#ifdef MCCTRL_RUST_HELPERS
static void sysfsm_work_main(struct work_struct *work0);
#endif

static struct sysfs_ops the_ops;
static struct kobj_type the_ktype;
static struct sysfsm_ops remote_ops;
static struct sysfsm_ops local_ops;

#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,0,0)
static inline int
bitmap_scnprintf(char *buf, unsigned buflen, const unsigned long *maskp, int nmaskbits)
{
	return scnprintf(buf, buflen, "%*pb\n", nmaskbits, maskp);
} /* bitmap_scnprintf() */

static inline int
bitmap_scnlistprintf(char *buf, unsigned buflen, const unsigned long *maskp, int nmaskbits)
{
	return scnprintf(buf, buflen, "%*pbl\n", nmaskbits, maskp);
} /* bitmap_scnlistprintf() */
#endif

#ifdef MCCTRL_RUST_HELPERS
enum {
	MCCTRL_SYSFS_REMOTE_STAGE_OK = 0,
	MCCTRL_SYSFS_REMOTE_STAGE_NOT_INIT = 1,
	MCCTRL_SYSFS_REMOTE_STAGE_DOWN = 2,
	MCCTRL_SYSFS_REMOTE_STAGE_WAIT0 = 3,
	MCCTRL_SYSFS_REMOTE_STAGE_TOO_LARGE = 4,
	MCCTRL_SYSFS_REMOTE_STAGE_SEND = 5,
	MCCTRL_SYSFS_REMOTE_STAGE_WAIT = 6,
	MCCTRL_SYSFS_REMOTE_STAGE_RESULT = 7,
};

static int
mcctrl_sysfs_down_bridge(void *sem)
{
	return down_interruptible(sem);
}

static void
mcctrl_sysfs_up_bridge(void *sem)
{
	up(sem);
}

static int
mcctrl_sysfs_wait_ready_bridge(void *req0)
{
	struct sysfsm_req *req = req0;

	return wait_event_interruptible(req->wq, !req->busy);
}

static void
mcctrl_sysfs_set_busy_bridge(void *req0, int busy)
{
	struct sysfsm_req *req = req0;

	req->busy = busy;
}

static int
mcctrl_sysfs_send_bridge(void *os, int cpu, int msg, long arg1, long arg2,
			 long arg3, int err)
{
	struct ikc_scd_packet packet;

	packet.msg = msg;
	packet.sysfs_arg1 = arg1;
	packet.sysfs_arg2 = arg2;
	packet.sysfs_arg3 = arg3;
	packet.err = err;
	return mcctrl_ikc_send(os, cpu, &packet);
}

static long
mcctrl_sysfs_req_lresult_bridge(void *req0)
{
	struct sysfsm_req *req = req0;

	return req->lresult;
}

static void
mcctrl_sysfs_copy_bridge(void *dst, const void *src, unsigned long size)
{
	memcpy(dst, src, size);
}

static void
mcctrl_sysfs_remote_show_stage_log(int stage, long error, unsigned long size)
{
	switch (stage) {
	case MCCTRL_SYSFS_REMOTE_STAGE_NOT_INIT:
		eprintk("mcctrl:remote_show:not initialized. %ld\n", error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_DOWN:
		eprintk("mcctrl:remote_show:down failed. %ld\n", error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT0:
		eprintk("mcctrl:remote_show:wait_event_interruptible0 failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_SEND:
		eprintk("mcctrl:remote_show:mcctrl_ikc_send failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT:
		eprintk("mcctrl:remote_show:wait_event_interruptible failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_RESULT:
		eprintk("mcctrl:remote_show:SCD_MSG_SYSFS_REQ_SHOW failed. %ld\n",
				error);
		break;
	default:
		break;
	}
	(void)size;
}

static void
mcctrl_sysfs_remote_store_stage_log(int stage, long error, unsigned long size)
{
	switch (stage) {
	case MCCTRL_SYSFS_REMOTE_STAGE_NOT_INIT:
		eprintk("mcctrl:remote_store:not initialized. %ld\n", error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_DOWN:
		eprintk("mcctrl:remote_store:down failed. %ld\n", error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT0:
		eprintk("mcctrl:remote_store:wait_event_interruptible0 failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_TOO_LARGE:
		eprintk("mcctrl:remote_store:too large size %#lx. %ld\n",
				size, error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_SEND:
		eprintk("mcctrl:remote_store:mcctrl_ikc_send failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT:
		eprintk("mcctrl:remote_store:wait_event_interruptible failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_RESULT:
		eprintk("mcctrl:remote_store:SCD_MSG_SYSFS_REQ_STORE failed. %ld\n",
				error);
		break;
	default:
		break;
	}
}

static void
mcctrl_sysfs_remote_release_stage_log(int stage, long error)
{
	switch (stage) {
	case MCCTRL_SYSFS_REMOTE_STAGE_DOWN:
		eprintk("mcctrl:remote_release:down failed. %ld\n", error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT0:
		eprintk("mcctrl:remote_release:wait_event_interruptible0 failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_SEND:
		eprintk("mcctrl:remote_release:mcctrl_ikc_send failed. %ld\n",
				error);
		break;
	case MCCTRL_SYSFS_REMOTE_STAGE_WAIT:
		eprintk("mcctrl:remote_release:wait_event_interruptible failed. %ld\n",
				error);
		break;
	default:
		break;
	}
}
#endif

static ssize_t
remote_show(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	int error;
	int stage = MCCTRL_SYSFS_REMOTE_STAGE_OK;
	struct sysfsm_node *np = instance;
	ssize_t ssize;
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;
#else
	int error;
	struct semaphore *held_sem = NULL;
	struct ikc_scd_packet packet;
	struct sysfsm_node *np = instance;
	ssize_t ssize = -EIO;
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;
#endif

	dprintk("mcctrl:remote_show(%p,%p,%p,%#lx)\n",
			ops, instance, buf, bufsize);

	sdp = np->sdp;
	req = &sdp->sysfs_req;

#ifdef MCCTRL_RUST_HELPERS
	ssize = mcctrl_sysfs_remote_show_body_result(np, buf, bufsize,
			sdp->sysfs_buf, sdp->sysfs_os, &sdp->sysfs_io_sem, req,
			np->client_ops, np->client_instance, &stage,
			mcctrl_sysfs_down_bridge, mcctrl_sysfs_up_bridge,
			mcctrl_sysfs_wait_ready_bridge,
			mcctrl_sysfs_set_busy_bridge, mcctrl_sysfs_send_bridge,
			mcctrl_sysfs_req_lresult_bridge,
			mcctrl_sysfs_copy_bridge);
	error = (ssize < 0) ? ssize : 0;
	mcctrl_sysfs_remote_show_stage_log(stage, error, bufsize);
#else
	if (!mcctrl_sysfs_inited_result((unsigned long)sdp->sysfs_buf)) {
		/* emulate EOF */
		error = 0;
		ssize = 0;
		eprintk("mcctrl:remote_show:not initialized. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_io_sem);
	if (error) {
		eprintk("mcctrl:remote_show:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_io_sem;

	/* for the case that last wait_event_interruptible() was interrupted */
	error = wait_event_interruptible(req->wq, !req->busy);
	if (error) {
		eprintk("mcctrl:remote_show:wait_event_interruptible0 failed. %d\n",
				error);
		error = -EINTR;
		goto out;
	}

	packet.msg = SCD_MSG_SYSFS_REQ_SHOW;
	packet.sysfs_arg1 = (long)np;
	packet.sysfs_arg2 = (long)np->client_ops;
	packet.sysfs_arg3 = (long)np->client_instance;

	req->busy = 1;
#define SYSFS_MCK_CPU 0
	error = mcctrl_ikc_send(sdp->sysfs_os, SYSFS_MCK_CPU, &packet);
	if (error) {
		eprintk("mcctrl:remote_show:mcctrl_ikc_send failed. %d\n",
				error);
		goto out;
	}

	error = wait_event_interruptible(req->wq, !req->busy);
	if (error) {
		eprintk("mcctrl:remote_show:wait_event_interruptible failed. %d\n",
				error);
		error = -EINTR;
		goto out;
	}

	ssize = req->lresult;
	if (ssize < 0) {
		error = ssize;
		eprintk("mcctrl:remote_show:SCD_MSG_SYSFS_REQ_SHOW failed. %d\n",
				error);
		goto out;
	}

	if (ssize > 0) {
		memcpy(buf, sdp->sysfs_buf, ssize);
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
#endif
	if (error) {
		eprintk("mcctrl:remote_show(%p,%p,%p,%#lx): %d\n",
				ops, instance, buf, bufsize, error);
		ssize = error;
	}
	dprintk("mcctrl:remote_show(%p,%p,%p,%#lx): %ld %d\n",
			ops, instance, buf, bufsize, ssize, error);
	return ssize;
} /* remote_show() */

static ssize_t
remote_store(struct sysfsm_ops *ops, void *instance, const void *buf,
		size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	int error;
	int stage = MCCTRL_SYSFS_REMOTE_STAGE_OK;
	struct sysfsm_node *np = instance;
	ssize_t ssize;
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;
#else
	int error;
	struct semaphore *held_sem = NULL;
	struct ikc_scd_packet packet;
	struct sysfsm_node *np = instance;
	ssize_t ssize = -EIO;
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;
#endif

	dprintk("mcctrl:remote_store(%p,%p,%p,%#lx)\n",
			ops, instance, buf, bufsize);

	sdp = np->sdp;
	req = &sdp->sysfs_req;

#ifdef MCCTRL_RUST_HELPERS
	ssize = mcctrl_sysfs_remote_store_body_result(np, buf, bufsize,
			sdp->sysfs_buf, sdp->sysfs_bufsize, sdp->sysfs_os,
			&sdp->sysfs_io_sem, req, np->client_ops,
			np->client_instance, &stage, mcctrl_sysfs_down_bridge,
			mcctrl_sysfs_up_bridge, mcctrl_sysfs_wait_ready_bridge,
			mcctrl_sysfs_set_busy_bridge, mcctrl_sysfs_send_bridge,
			mcctrl_sysfs_req_lresult_bridge,
			mcctrl_sysfs_copy_bridge);
	error = (ssize < 0) ? ssize : 0;
	mcctrl_sysfs_remote_store_stage_log(stage, error, bufsize);
#else
	if (!mcctrl_sysfs_inited_result((unsigned long)sdp->sysfs_buf)) {
		/* emulate EOF */
		error = -ENOSPC;
		eprintk("mcctrl:remote_store:not initialized. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_io_sem);
	if (error) {
		eprintk("mcctrl:remote_store:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_io_sem;

	/* for the case that last wait_event_interruptible() was interrupted */
	error = wait_event_interruptible(req->wq, !req->busy);
	if (error) {
		eprintk("mcctrl:remote_store:wait_event_interruptible0 failed. %d\n",
				error);
		error = -EINTR;
		goto out;
	}

	if (bufsize > sdp->sysfs_bufsize) {
		error = -ENOSPC;
		eprintk("mcctrl:remote_store:too large size %#lx. %d\n",
				bufsize, error);
		goto out;
	}

	memcpy(sdp->sysfs_buf, buf, bufsize);

	packet.msg = SCD_MSG_SYSFS_REQ_STORE;
	packet.sysfs_arg1 = (long)np;
	packet.sysfs_arg2 = (long)np->client_ops;
	packet.sysfs_arg3 = (long)np->client_instance;
	packet.err = bufsize;

	req->busy = 1;
#define SYSFS_MCK_CPU 0
	error = mcctrl_ikc_send(sdp->sysfs_os, SYSFS_MCK_CPU, &packet);
	if (error) {
		eprintk("mcctrl:remote_store:mcctrl_ikc_send failed. %d\n",
				error);
		goto out;
	}

	error = wait_event_interruptible(req->wq, !req->busy);
	if (error) {
		eprintk("mcctrl:remote_store:wait_event_interruptible failed. %d\n",
				error);
		error = -EINTR;
		goto out;
	}

	ssize = req->lresult;
	if (ssize < 0) {
		error = ssize;
		eprintk("mcctrl:remote_store:SCD_MSG_SYSFS_REQ_STORE failed. %d\n",
				error);
		goto out;
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
#endif
	if (error) {
		eprintk("mcctrl:remote_store(%p,%p,%p,%#lx): %d\n",
				ops, instance, buf, bufsize, error);
		ssize = error;
	}
	dprintk("mcctrl:remote_store(%p,%p,%p,%#lx): %ld %d\n",
			ops, instance, buf, bufsize, ssize, error);
	return ssize;
} /* remote_store() */

static int
release_i(struct sysfsm_node *np)
{
	int error;
	struct sysfsm_data *sdp;

	BUG_ON(!np);
	dprintk("mcctrl:release_i(%p %s)\n", np, np->name);

	sdp = np->sdp;

	if (np->type != SNT_DIR) {
		if (np->server_ops && np->server_ops->release) {
			(*np->server_ops->release)(np->server_ops, np);
		}
	}
	kfree(np->name);
	kfree(np);

	error = 0;
#if 0
out:
#endif
	if (error) {
		eprintk("mcctrl:release_i(%p %s): %d\n", np, np->name, error);
	}
	dprintk("mcctrl:release_i(%p): %d\n", np, error);
	return error;
} /* release_i() */

static void
remote_release(struct sysfsm_ops *ops, void *instance)
{
	int error;
#ifdef MCCTRL_RUST_HELPERS
	int stage = MCCTRL_SYSFS_REMOTE_STAGE_OK;
#else
	struct semaphore *held_sem = NULL;
	struct ikc_scd_packet packet;
#endif
	struct sysfsm_node *np = instance;
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;

	dprintk("mcctrl:remote_release(%p,%p)\n", ops, instance);

	sdp = np->sdp;
	req = &sdp->sysfs_req;
#ifdef MCCTRL_RUST_HELPERS
	error = mcctrl_sysfs_remote_release_body_result(np, np->type,
			sdp->sysfs_buf, sdp->sysfs_os, &sdp->sysfs_io_sem,
			req, np->client_ops, np->client_instance, SNT_FILE,
			&stage, mcctrl_sysfs_down_bridge,
			mcctrl_sysfs_up_bridge,
			mcctrl_sysfs_wait_ready_bridge,
			mcctrl_sysfs_set_busy_bridge, mcctrl_sysfs_send_bridge);
	mcctrl_sysfs_remote_release_stage_log(stage, error);
#else
	if ((np->type == SNT_FILE) && np->client_ops &&
			mcctrl_sysfs_inited_result((unsigned long)sdp->sysfs_buf)) {
		error = down_interruptible(&sdp->sysfs_io_sem);
		if (error) {
			eprintk("mcctrl:remote_release:down failed. %d\n",
					error);
			goto out;
		}
		held_sem = &sdp->sysfs_io_sem;

		/* for the case that last wait_event_interruptible() was interrupted */
		error = wait_event_interruptible(req->wq, !req->busy);
		if (error) {
			eprintk("mcctrl:remote_release:wait_event_interruptible0 failed. %d\n",
					error);
			error = -EINTR;
			goto out;
		}

		packet.msg = SCD_MSG_SYSFS_REQ_RELEASE;
		packet.sysfs_arg1 = (long)np;
		packet.sysfs_arg2 = np->client_ops;
		packet.sysfs_arg3 = np->client_instance;

		req->busy = 1;
#define SYSFS_MCK_CPU 0
		error = mcctrl_ikc_send(sdp->sysfs_os, SYSFS_MCK_CPU, &packet);
		if (error) {
			eprintk("mcctrl:remote_release:mcctrl_ikc_send failed. %d\n",
					error);
			goto out;
		}

		error = wait_event_interruptible(req->wq, !req->busy);
		if (error) {
			eprintk("mcctrl:remote_release:wait_event_interruptible failed. %d\n",
					error);
			error = -EINTR;
			goto out;
		}
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
#endif
	if (error) {
		eprintk("mcctrl:remote_release(%p,%p): %d\n",
				ops, instance, error);
	}
	dprintk("mcctrl:remote_release(%p,%p): %d\n", ops, instance, error);
	return;
} /* remote_release() */

#ifdef MCCTRL_RUST_HELPERS
static int mcctrl_sysfs_node_type_bridge(void *instance);

static const char *
mcctrl_sysfs_node_name_bridge(void *node)
{
	return ((struct sysfsm_node *)node)->name;
}

static void *
mcctrl_sysfs_first_child_bridge(void *node)
{
	struct sysfsm_node *np = node;

	if (list_empty(&np->children))
		return NULL;
	return list_first_entry(&np->children, struct sysfsm_node, chain);
}

static void *
mcctrl_sysfs_next_child_bridge(void *parent, void *node)
{
	struct sysfsm_node *dirp = parent;
	struct list_head *next = ((struct sysfsm_node *)node)->chain.next;

	if (next == &dirp->children)
		return NULL;
	return list_entry(next, struct sysfsm_node, chain);
}

static void *
mcctrl_sysfs_err_ptr_bridge(int error)
{
	return ERR_PTR(error);
}
#endif

static struct sysfsm_node *
lookup_i(struct sysfsm_node *dirp, const char *name)
{
#ifdef MCCTRL_RUST_HELPERS
	BUG_ON(!dirp);
	BUG_ON(!name);
	dprintk("mcctrl:lookup_i(%s,%s)\n", dirp->name, name);

	return mcctrl_sysfs_lookup_i_body_result(
		dirp, name, SNT_DIR, mcctrl_sysfs_node_type_bridge,
		mcctrl_sysfs_node_name_bridge,
		mcctrl_sysfs_first_child_bridge,
		mcctrl_sysfs_next_child_bridge,
		mcctrl_sysfs_err_ptr_bridge);
#else
	int error;
	struct sysfsm_node *np;

	BUG_ON(!dirp);
	BUG_ON(!name);
	dprintk("mcctrl:lookup_i(%s,%s)\n", dirp->name, name);

	if (dirp->type != SNT_DIR) {
		error = -ENOTDIR;
		eprintk("mcctrl:lookup_i:not a directory. %d\n", error);
		goto out;
	}

	if (name[0] == '\0') {
		error = -ENOENT;
		eprintk("mcctrl:lookup_i:null component. %d\n", error);
		goto out;
	}

	list_for_each_entry(np, &dirp->children, chain) {
		if (!strcmp(np->name, name)) {
			/* found */
			error = 0;
			goto out;
		}
	}

	/* this is usual when called from create_i(), mkdir_i() and symlink_i(). */
	error = ENOENT; /* positive value means suppressing error message */
out:
	if (error) {
		if (error < 0) {
			eprintk("mcctrl:lookup_i(%s,%s): %d\n",
					dirp->name, name, error);
		}
		else {
			error = -error;
		}
		np = ERR_PTR(error);
	}
	dprintk("mcctrl:lookup_i(%s,%s): %p %d\n",
			dirp->name, name, np, error);
	return np;
#endif
} /* lookup_i() */

static struct sysfsm_node *
create_i(struct sysfsm_node *parent, const char *name, mode_t mode,
		struct sysfsm_ops *server_ops, long client_ops,
		long client_instance)
{
	int error;
	struct sysfsm_node *np = NULL;
	struct sysfsm_data *sdp;

	BUG_ON(!parent);
	BUG_ON(!name);
	dprintk("mcctrl:create_i(%s,%s,%#o,%#lx,%#lx)\n",
			parent->name, name, mode, client_ops, client_instance);

	sdp = parent->sdp;

	if (parent == sdp->sysfs_root) {
		error = -EPERM;
		eprintk("mcctrl:create_i:root dir. %d\n", error);
		goto out;
	}

	if (parent->type != SNT_DIR) {
		error = -ENOTDIR;
		eprintk("mcctrl:create_i:not a directory. %d\n", error);
		goto out;
	}

	if (name[0] == '\0') {
		error = -EINVAL;
		eprintk("mcctrl:create_i:null filename. %d\n", error);
		goto out;
	}

	np = lookup_i(parent, name);
	if (!IS_ERR(np)) {
		error = -EEXIST;
		eprintk("mcctrl:create_i:already exist. %d\n", error);
		np = NULL;
		goto out;
	}

	np = kzalloc(sizeof(*np), GFP_KERNEL);
	if (!np) {
		error = -ENOMEM;
		eprintk("mcctrl:create_i:kzalloc failed. %d\n", error);
		goto out;
	}

	np->type = SNT_FILE;
	np->name = kstrdup(name, GFP_KERNEL);
	np->parent = parent;
	np->sdp = sdp;
	INIT_LIST_HEAD(&np->chain);
	np->attr.name = np->name;
	np->attr.mode = mode;
	np->server_ops = server_ops;
	np->client_ops = client_ops;
	np->client_instance = client_instance;

	if (!np->name) {
		error = -ENOMEM;
		eprintk("mcctrl:create_i:kstrdup failed. %d\n", error);
		goto out;
	}

	error = sysfs_create_file(&parent->kobj, &np->attr);
	if (error) {
		eprintk("mcctrl:create_i:sysfs_create_file failed. %d\n",
				error);
		goto out;
	}

	list_add(&np->chain, &parent->children);

	error = 0;
out:
	if (error) {
		if (np) {
			kfree(np->name);
			kfree(np);
		}
		np = ERR_PTR(error);
		eprintk("mcctrl:create_i(%s,%s,%#o,%#lx,%#lx) : %d\n",
				parent->name, name, mode, client_ops,
				client_instance, error);
	}
	dprintk("mcctrl:create_i(%s,%s,%#o,%#lx,%#lx) : %p %d\n",
			parent->name, name, mode, client_ops, client_instance,
			np, error);
	return np;
} /* create_i() */

static struct sysfsm_node *
mkdir_i(struct sysfsm_node *parent, const char *name)
{
	int error;
	struct sysfsm_node *np = NULL;
	struct kobject *parent_kobj;
	struct sysfsm_data *sdp;

	BUG_ON(!parent);
	BUG_ON(!name);
	dprintk("mcctrl:mkdir_i(%s,%s)\n", parent->name, name);

	sdp = parent->sdp;

	if ((parent == sdp->sysfs_root) && strcmp(name, "sys")) {
		error = -EPERM;
		eprintk("mcctrl:mkdir_i:root dir. %d\n", error);
		goto out;
	}

	if (parent->type != SNT_DIR) {
		error = -ENOTDIR;
		eprintk("mcctrl:mkdir_i:not a directory. %d\n", error);
		goto out;
	}

	if (name[0] == '\0') {
		error = -EINVAL;
		eprintk("mcctrl:mkdir_i:null dirname. %d\n", error);
		goto out;
	}

	np = lookup_i(parent, name);
	if (!IS_ERR(np)) {
		error = -EEXIST;
		eprintk("mcctrl:mkdir_i:already exist. %d\n", error);
		np = NULL;
		goto out;
	}

	np = kzalloc(sizeof(*np), GFP_KERNEL);
	if (!np) {
		error = -ENOMEM;
		eprintk("mcctrl:mkdir_i:kzalloc failed. %d\n", error);
		goto out;
	}

	np->type = SNT_DIR;
	np->name = kstrdup(name, GFP_KERNEL);
	np->parent = parent;
	np->sdp = sdp;
	INIT_LIST_HEAD(&np->chain);
	INIT_LIST_HEAD(&np->children);

	if (!np->name) {
		error = -ENOMEM;
		eprintk("mcctrl:mkdir_i:kstrdup failed. %d\n", error);
		goto out;
	}

	parent_kobj = &parent->kobj;
	if (parent == sdp->sysfs_root) {
		parent_kobj = sdp->sysfs_kobj;
	}

	error = kobject_init_and_add(&np->kobj, &the_ktype, parent_kobj,
			np->name);
	if (error) {
		eprintk("mcctrl:mkdir_i:kobject_init_and_add failed. %d\n",
				error);
		goto out;
	}

	list_add(&np->chain, &parent->children);

	error = 0;
out:
	if (error) {
		if (np) {
			kfree(np->name);
			kfree(np);
		}
		np = ERR_PTR(error);
		eprintk("mcctrl:mkdir_i(%s,%s): %d\n",
				parent->name, name, error);
	}
	dprintk("mcctrl:mkdir_i(%s,%s): %p %d\n",
			parent->name, name, np, error);
	return np;
} /* mkdir_i() */

static struct sysfsm_node *
symlink_i(struct sysfsm_node *target, struct sysfsm_node *parent,
		const char *name)
{
	int error;
	struct sysfsm_node *np = NULL;
	struct sysfsm_data *sdp;

	BUG_ON(!target);
	BUG_ON(!parent);
	BUG_ON(!name);
	dprintk("mcctrl:symlink_i(%s,%s,%s)\n",
			target->name, parent->name, name);

	sdp = parent->sdp;

	if (target->type != SNT_DIR) {
		error = -EINVAL;
		eprintk("mcctrl:symlink_i:target isn't a directory. %d\n",
				error);
		goto out;
	}

	if (parent == sdp->sysfs_root) {
		error = -EPERM;
		eprintk("mcctrl:symlink_i:root directory. %d\n", error);
		goto out;
	}

	if (parent->type != SNT_DIR) {
		error = -ENOTDIR;
		eprintk("mcctrl:symlink_i:parent isn't a directory. %d\n",
				error);
		goto out;
	}

	if (name[0] == '\0') {
		error = -EINVAL;
		eprintk("mcctrl:symlink_i:null linkname. %d\n", error);
		goto out;
	}

	np = lookup_i(parent, name);
	if (!IS_ERR(np)) {
		error = -EEXIST;
		eprintk("mcctrl:symlink_i:already exist. %d\n", error);
		np = NULL;
		goto out;
	}

	np = kzalloc(sizeof(*np), GFP_KERNEL);
	if (!np) {
		error = -ENOMEM;
		eprintk("mcctrl:symlink_i:kzalloc failed. %d\n", error);
		goto out;
	}

	np->type = SNT_LINK;
	np->name = kstrdup(name, GFP_KERNEL);
	np->parent = parent;
	np->sdp = sdp;
	INIT_LIST_HEAD(&np->chain);

	if (!np->name) {
		error = -ENOMEM;
		eprintk("mcctrl:symlink_i:kstrdup failed. %d\n", error);
		goto out;
	}

	error = sysfs_create_link(&parent->kobj, &target->kobj, name);
	if (error) {
		eprintk("mcctrl:symlink_i:sysfs_create_link failed. %d\n",
				error);
		goto out;
	}

	list_add(&np->chain, &parent->children);

	error = 0;
out:
	if (error) {
		if (np) {
			kfree(np->name);
			kfree(np);
		}
		np = ERR_PTR(error);
		eprintk("mcctrl:symlink_i(%s,%s,%s): %d\n",
				target->name, parent->name, name, error);
	}
	dprintk("mcctrl:symlink_i(%s,%s,%s): %p %d\n",
			target->name, parent->name, name, np, error);
	return np;
} /* symlink_i() */

static int
unlink_i(struct sysfsm_node *np)
{
	int error;
	struct sysfsm_data *sdp;

	BUG_ON(!np);
	dprintk("mcctrl:unlink_i(%s)\n", np->name);

	sdp = np->sdp;

	if ((np == sdp->sysfs_root) || (np->parent == sdp->sysfs_root)) {
		error = -EPERM;
		eprintk("mcctrl:unlink_i:protected directory. %d\n", error);
		goto out;
	}

	if ((np->type == SNT_DIR) && !list_empty(&np->children)) {
		error = -ENOTEMPTY;
		eprintk("mcctrl:unlink_i:not empty dir. %d\n", error);
		goto out;
	}

	list_del(&np->chain);
	if (np->type == SNT_FILE) {
		sysfs_remove_file(&np->parent->kobj, &np->attr);
	}
	else if (np->type == SNT_DIR) {
		if (np->parent != np) {
			kobject_del(&np->kobj);
		}
	}
	else if (np->type == SNT_LINK) {
		sysfs_remove_link(&np->parent->kobj, np->name);
	}
	else {
		BUG();
	}

	error = release_i(np);
	if (error) {
		eprintk("mcctrl:unlink_i:release_i failed. %d\n", error);
		goto out;
	}

	error = 0;
out:
	if (error) {
		eprintk("mcctrl:unlink_i(%s): %d\n", np->name, error);
	}
	dprintk("mcctrl:unlink_i(%s): %d\n", (!error)?NULL:np->name, error);
	return error;
} /* unlink_i() */

static int
remove(struct sysfsm_node *target)
{
	int error;
	struct sysfsm_node *np;
	struct sysfsm_node *next_np;

	BUG_ON(!target);
	dprintk("mcctrl:remove(%s)\n", target->name);

	for (np = target; np; np = next_np) {
		while ((np->type == SNT_DIR) && !list_empty(&np->children)) {
			np = list_first_entry(&np->children,
					struct sysfsm_node, chain);
		}

		next_np = np->parent;
		if (np == target) {
			next_np = NULL;
		}

		error = unlink_i(np);
		if (error) {
			eprintk("mcctrl:remove:unlink_i(%s) failed. %d\n",
					np->name, error);
			goto out;
		}
	}

	error = 0;
out:
	if (error) {
		eprintk("mcctrl:remove(%s): %d\n", target->name, error);
	}
	dprintk("mcctrl:remove(%s): %d\n", (!error)?NULL:target->name, error);
	return error;
} /* remove() */

static struct sysfsm_node *
lookup(struct sysfsm_node *from, char *path)
{
	int error;
	struct sysfsm_node *dirp;
	struct sysfsm_node *np;
	char *p;
	char *name;

	BUG_ON(!from);
	BUG_ON(!path);
	dprintk("mcctrl:lookup(%s,%s)\n", from->name, path);

	dirp = from;
	np = from;
	p = path;
	while (!!(name = strsep(&p, "/"))) {
		if (!*name) {
			continue;
		}

		np = lookup_i(dirp, name);
		if (IS_ERR(np)) {
			error = PTR_ERR(np);
			eprintk("mcctrl:lookup:lookup_i(%s,%s) failed. %d\n",
					dirp->name, name, error);
			goto out;
		}
		dirp = np;
	}

	error = 0;
out:
	if (error) {
		np = ERR_PTR(error);
		eprintk("mcctrl:lookup(%s,%s): %d\n", from->name, path, error);
	}
	dprintk("mcctrl:lookup(%s,%s): %p %d\n", from->name, path, np, error);
	return np;
} /* lookup() */

static struct sysfsm_node *
dig(struct sysfsm_node *from, char *path)
{
	int error;
	struct sysfsm_node *dirp;
	char *p;
	char *name;
	struct sysfsm_node *np;

	BUG_ON(!from);
	BUG_ON(!path);
	dprintk("mcctrl:dig(%s,%s)\n", from->name, path);

	dirp = from;
	p = path;
	while (!!(name = strsep(&p, "/"))) {
		if (!*name) {
			continue;
		}

		np = lookup_i(dirp, name);
		if (IS_ERR(np)) {
			error = PTR_ERR(np);
			if (error != -ENOENT) {
				eprintk("mcctrl:dig:lookup_i(%s,%s) failed. %d\n",
						dirp->name, name, error);
				goto out;
			}

			np = mkdir_i(dirp, name);
			if (IS_ERR(np)) {
				error = PTR_ERR(np);
				eprintk("mcctrl:dig:mkdir_i(%s,%s) failed. %d\n",
						dirp->name, name, error);
				goto out;
			}
		}
		dirp = np;
	}

	if (dirp->type != SNT_DIR) {
		error = -ENOTDIR;
		eprintk("mcctrl:dig:%s:not a directory. %d\n",
				dirp->name, error);
		goto out;
	}

	error = 0;
out:
	if (error) {
		dirp = ERR_PTR(error);
		eprintk("mcctrl:dig(%s): %d\n", from->name, error);
	}
	dprintk("mcctrl:dig(%s): %p %d\n", from->name, dirp, error);
	return dirp;
} /* dig() */

static void
cleanup_ancestor(struct sysfsm_node *target)
{
	int error;
	struct sysfsm_node *np;
	struct sysfsm_node *next_np;

	BUG_ON(!target);
	dprintk("mcctrl:cleanup_ancestor(%p {%s})\n", target, target->name);

	error = 0;
	for (np = target; !error; np = next_np) {
		next_np = np->parent;

		if ((np == np->sdp->sysfs_root)
				|| (np->parent == np->sdp->sysfs_root)
				|| !list_empty(&np->children)) {
			break;
		}

		error = unlink_i(np);
	}

	dprintk("mcctrl:cleanup_ancestor(%p):\n", target);
	return;
} /* cleanup_ancestor() */

static struct sysfsm_node *
sysfsm_create(struct sysfsm_data *sdp, const char *path0, mode_t mode,
		struct sysfsm_ops *server_ops, long client_ops,
		long client_instance)
{
	int error;
	char *path = NULL;
	struct semaphore *held_sem = NULL;
	struct sysfsm_node *dirp;
	char *name;
	struct sysfsm_node *np = ERR_PTR(-EIO);

	BUG_ON(!sdp);
	dprintk("mcctrl:sysfsm_create(%p,%s,%#o,%#lx,%#lx)\n",
			sdp, path0, mode, client_ops, client_instance);

	path = kstrdup(path0, GFP_KERNEL);
	if (!path) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_create:kstrdup failed. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_tree_sem);
	if (error) {
		eprintk("mcctrl:sysfsm_create:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_tree_sem;

	dirp = sdp->sysfs_root;
	name = strrchr(path, '/');
	if (!name) {
		name = path;
	}
	else {
		*name = '\0';
		++name;

		dirp = dig(dirp, path);
		if (IS_ERR(dirp)) {
			error = PTR_ERR(dirp);
			eprintk("mcctrl:sysfsm_create:dig failed. %d\n",
					error);
			goto out;
		}
	}

	np = create_i(dirp, name, mode, server_ops, client_ops,
			client_instance);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_create:create_i(%s,%s) failed. %d\n",
				dirp->name, name, error);
		goto out;
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
	kfree(path);
	if (error) {
		np = ERR_PTR(error);
		eprintk("mcctrl:sysfsm_create(%p,%s,%#o,%#lx,%#lx): %d\n",
				sdp, path0, mode, client_ops, client_instance,
				error);
	}
	dprintk("mcctrl:sysfsm_create(%p,%s,%#o,%#lx,%#lx): %p %d\n",
			sdp, path0, mode, client_ops, client_instance, np,
			error);
	return np;
} /* sysfsm_create() */

struct sysfsm_node *
sysfsm_mkdir(struct sysfsm_data *sdp, const char *path0)
{
	int error;
	char *path = NULL;
	struct semaphore *held_sem = NULL;
	struct sysfsm_node *dirp;
	char *name;
	struct sysfsm_node *np = ERR_PTR(-EIO);

	BUG_ON(!sdp);
	dprintk("mcctrl:sysfsm_mkdir(%p,%s)\n", sdp, path0);

	path = kstrdup(path0, GFP_KERNEL);
	if (!path) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_mkdir:kstrdup failed. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_tree_sem);
	if (error) {
		eprintk("mcctrl:sysfsm_mkdir:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_tree_sem;

	dirp = sdp->sysfs_root;
	name = strrchr(path, '/');
	if (!name) {
		name = path;
	}
	else {
		*name = '\0';
		++name;

		dirp = dig(dirp, path);
		if (IS_ERR(dirp)) {
			error = PTR_ERR(dirp);
			eprintk("mcctrl:sysfsm_mkdir:dig failed. %d\n", error);
			goto out;
		}
	}

	np = mkdir_i(dirp, name);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_mkdir:mkdir_i failed. %d\n", error);
		goto out;
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
	kfree(path);
	if (error) {
		np = ERR_PTR(error);
		eprintk("mcctrl:sysfsm_mkdir(%p,%s): %d\n", sdp, path0, error);
	}
	dprintk("mcctrl:sysfsm_mkdir(%p,%s): %p %d\n", sdp, path0, np, error);
	return np;
} /* sysfsm_mkdir() */

struct sysfsm_node *
sysfsm_symlink(struct sysfsm_data *sdp, struct sysfsm_node *target,
		const char *path0)
{
	int error;
	char *path = NULL;
	struct semaphore *held_sem = NULL;
	char *name;
	struct sysfsm_node *dirp;
	struct sysfsm_node *np = ERR_PTR(-EIO);

	BUG_ON(!sdp);
	BUG_ON(!target);
	dprintk("mcctrl:sysfsm_symlink(%p,%s,%s)\n", sdp, target->name, path0);

	path = kstrdup(path0, GFP_KERNEL);
	if (!path) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_symlink:kstrdup failed. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_tree_sem);
	if (error) {
		eprintk("mcctrl:sysfsm_symlink:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_tree_sem;

	dirp = sdp->sysfs_root;
	name = strrchr(path, '/');
	if (!name) {
		name = path;
	}
	else {
		*name = '\0';
		++name;

		dirp = dig(dirp, path);
		if (IS_ERR(dirp)) {
			error = PTR_ERR(dirp);
			eprintk("mcctrl:sysfsm_symlink:dig failed. %d\n",
					error);
			goto out;
		}
	}

	np = symlink_i(target, dirp, name);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_symlink:symlink_i(%s,%s,%s) failed. %d\n",
				target->name, dirp->name, name, error);
		goto out;
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
	kfree(path);
	if (error) {
		np = ERR_PTR(error);
		eprintk("mcctrl:sysfsm_symlink(%p,%s,%s): %d\n",
				sdp, target->name, path0, error);
	}
	dprintk("mcctrl:sysfsm_symlink(%p,%s,%s): %p %d\n",
			sdp, target->name, path0, np, error);
	return np;
} /* sysfsm_symlink() */

static struct sysfsm_node *
sysfsm_lookup(struct sysfsm_data *sdp, const char *path0)
{
	int error;
	char *path = NULL;
	struct semaphore *held_sem = NULL;
	struct sysfsm_node *np;

	BUG_ON(!sdp);
	dprintk("mcctrl:sysfsm_lookup(%p,%s)\n", sdp, path0);

	path = kstrdup(path0, GFP_KERNEL);
	if (!path) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_lookup:kstrdup failed. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_tree_sem);
	if (error) {
		eprintk("mcctrl:sysfsm_lookup:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_tree_sem;

	np = lookup(sdp->sysfs_root, path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_lookup:lookup failed. %d\n", error);
		goto out;
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
	kfree(path);
	if (error) {
		np = ERR_PTR(error);
		eprintk("mcctrl:sysfsm_lookup(%p,%s): %d\n",
				sdp, path0, error);
	}
	dprintk("mcctrl:sysfsm_lookup(%p,%s): %p %d\n", sdp, path0, np, error);
	return np;
} /* sysfsm_lookup() */

static int
sysfsm_unlink(struct sysfsm_data *sdp, const char *path0, int flags)
{
	int error;
	char *path = NULL;
	struct semaphore *held_sem = NULL;
	struct sysfsm_node *dirp;
	struct sysfsm_node *np;

	BUG_ON(!sdp);
	dprintk("mcctrl:sysfsm_unlink(%p,%s,%#x)\n", sdp, path0, flags);

	path = kstrdup(path0, GFP_KERNEL);
	if (!path) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_unlink:kstrdup failed. %d\n", error);
		goto out;
	}

	error = down_interruptible(&sdp->sysfs_tree_sem);
	if (error) {
		eprintk("mcctrl:sysfsm_unlink:down failed. %d\n", error);
		goto out;
	}
	held_sem = &sdp->sysfs_tree_sem;

	np = lookup(sdp->sysfs_root, path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_unlink:lookup failed. %d\n", error);
		goto out;
	}

	dirp = np->parent;

	error = remove(np);
	if (error) {
		eprintk("mcctrl:sysfsm_unlink:remove failed. %d\n", error);
		goto out;
	}

	if (!(flags & SYSFS_UNLINK_KEEP_ANCESTOR)) {
		cleanup_ancestor(dirp);
	}

	error = 0;
out:
	if (held_sem) {
		up(held_sem);
	}
	kfree(path);
	if (error) {
		eprintk("mcctrl:sysfsm_unlink(%p,%s,%#x): %d\n",
				sdp, path0, flags, error);
	}
	dprintk("mcctrl:sysfsm_unlink(%p,%s,%#x): %d\n",
			sdp, path0, flags, error);
	return error;
} /* sysfsm_unlink() */

void
sysfsm_cleanup(ihk_os_t os)
{
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_data *sdp;
	struct sysfsm_node *np;

	if (!udp) {
		pr_warn("%s: warning: mcctrl_usrdata not found\n", __func__);
		return;
	}

	sdp = &udp->sysfsm_data;

	dprintk("mcctrl:sysfsm_cleanup(%p)\n", os);

	if (sdp->sysfs_buf) {
		ihk_device_unmap_virtual(dev, sdp->sysfs_buf,
				sdp->sysfs_bufsize);
		ihk_device_unmap_memory(dev, sdp->sysfs_buf_pa,
				sdp->sysfs_bufsize);
		sdp->sysfs_buf = NULL;
		sdp->sysfs_buf_pa = 0;
		sdp->sysfs_buf_rpa = 0;
	}

	np = sdp->sysfs_root;
	sdp->sysfs_root = NULL;

	if (np) {
		error = remove(np);
		if (error) {
			wprintk("mcctrl:sysfsm_cleanup:remove failed. %d\n",
					error);
			/* through */
		}
	}

	dprintk("mcctrl:sysfsm_cleanup(%p):\n", os);
	return;
} /* sysfsm_cleanup() */

int
sysfsm_setup(ihk_os_t os, void *buf, long buf_pa, size_t bufsize)
{
	int error;
	struct device *dev = ihk_os_get_linux_device(os);
	struct sysfsm_node *np = NULL;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_data *sdp;
	struct sysfsm_req *req;

	dprintk("mcctrl:sysfsm_setup(%p)\n", os);

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	sdp = &udp->sysfsm_data;
	req = &sdp->sysfs_req;

	req->busy = 0;
	init_waitqueue_head(&req->wq);

	np = kzalloc(sizeof(*np), GFP_KERNEL);
	if (!np) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_setup:kzalloc failed. %d\n", error);
		goto out;
	}

	np->type = SNT_DIR;
	np->name = kstrdup("(the_root)", GFP_KERNEL);
	np->parent = np;
	np->sdp = sdp;
	INIT_LIST_HEAD(&np->chain);
	INIT_LIST_HEAD(&np->children);

	if (!np->name) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_setup:kstrdup failed. %d\n", error);
		goto out;
	}

	sdp->sysfs_os = os;
	sdp->sysfs_kobj = &dev->kobj;
	sema_init(&sdp->sysfs_io_sem, 1);
	sema_init(&sdp->sysfs_tree_sem, 1);

	sdp->sysfs_root = np;
	np = NULL;

	np = mkdir_i(sdp->sysfs_root, "sys");
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_setup:mkdir_i failed. %d\n", error);
		goto out;
	}

	sdp->sysfs_bufsize = bufsize;
	sdp->sysfs_buf_pa = buf_pa;
	wmb();
	sdp->sysfs_buf = buf;

	setup_sysfs_files(os);

	error = 0;
out:
	if (error) {
		if (np) {
			kfree(np->name);
			kfree(np);
		}
		sysfsm_cleanup(os);
		eprintk("mcctrl:sysfsm_setup(%p): %d\n", os, error);
	}
	dprintk("mcctrl:sysfsm_setup(%p): %d\n", os, error);
	return error;
} /* sysfsm_setup() */

/***********************************************************************
 * remote snooping
 */
struct remote_snooping_param {
	ihk_device_t dev;
	int nbits;
	int size;
	long phys;
	void *ptr;
};

static void cleanup_special_remote_create(struct sysfsm_ops *ops, void *instance)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *param = (void *)np->client_instance;

	ihk_device_unmap_virtual(param->dev, param->ptr, param->size);
	ihk_device_unmap_memory(param->dev, param->phys, param->size);
	kfree(param);
	return;
} /* cleanup_special_remote_create() */

/**** remote int ****/
static ssize_t snooping_remote_show_d32(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%d\n", *(int *)p->ptr);
} /* snooping_remote_show_d32() */

static struct sysfsm_ops snooping_remote_ops_d32 = {
	.show = &snooping_remote_show_d32,
	.release = &cleanup_special_remote_create,
};

/**** remote long ****/
static ssize_t snooping_remote_show_d64(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%ld\n", *(long *)p->ptr);
} /* snooping_remote_show_d64() */

static struct sysfsm_ops snooping_remote_ops_d64 = {
	.show = &snooping_remote_show_d64,
	.release = &cleanup_special_remote_create,
};

/**** remote unsigned int ****/
static ssize_t snooping_remote_show_u32(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%u\n", *(unsigned *)p->ptr);
} /* snooping_remote_show_u32() */

static struct sysfsm_ops snooping_remote_ops_u32 = {
	.show = &snooping_remote_show_u32,
	.release = &cleanup_special_remote_create,
};

/**** remote unsigned long ****/
static ssize_t snooping_remote_show_u64(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%lu\n", *(unsigned long *)p->ptr);
} /* snooping_remote_show_u64() */

static struct sysfsm_ops snooping_remote_ops_u64 = {
	.show = &snooping_remote_show_u64,
	.release = &cleanup_special_remote_create,
};

/**** remote string ****/
static ssize_t snooping_remote_show_s(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%.*s\n", (int)p->size, (char *)p->ptr);
} /* snooping_remote_show_s() */

static struct sysfsm_ops snooping_remote_ops_s = {
	.show = &snooping_remote_show_s,
	.release = &cleanup_special_remote_create,
};

/**** remote list ****/
static ssize_t snooping_remote_show_pbl(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return bitmap_scnlistprintf(buf, bufsize, p->ptr, p->nbits);
} /* snooping_remote_show_pbl() */

static struct sysfsm_ops snooping_remote_ops_pbl = {
	.show = &snooping_remote_show_pbl,
	.release = &cleanup_special_remote_create,
};

/**** remote map ****/
static ssize_t snooping_remote_show_pb(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return bitmap_scnprintf(buf, bufsize, p->ptr, p->nbits);
} /* snooping_remote_show_pb() */

static struct sysfsm_ops snooping_remote_ops_pb = {
	.show = &snooping_remote_show_pb,
	.release = &cleanup_special_remote_create,
};

/**** remote K unsigned int ****/
static ssize_t snooping_remote_show_u32K(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
	struct sysfsm_node *np = instance;
	struct remote_snooping_param *p = (void *)np->client_instance;

	return sprintf(buf, "%uK\n", (*(unsigned *)p->ptr >> 10));
} /* snooping_remote_show_u32K() */

static struct sysfsm_ops snooping_remote_ops_u32K = {
	.show = &snooping_remote_show_u32K,
	.release = &cleanup_special_remote_create,
};

struct sysfsm_ops * const remote_snooping_ops_table[] = {
	[(long)SYSFS_SNOOPING_OPS_d32] = &snooping_remote_ops_d32,
	[(long)SYSFS_SNOOPING_OPS_d64] = &snooping_remote_ops_d64,
	[(long)SYSFS_SNOOPING_OPS_u32] = &snooping_remote_ops_u32,
	[(long)SYSFS_SNOOPING_OPS_u64] = &snooping_remote_ops_u64,
	[(long)SYSFS_SNOOPING_OPS_s] = &snooping_remote_ops_s,
	[(long)SYSFS_SNOOPING_OPS_pbl] = &snooping_remote_ops_pbl,
	[(long)SYSFS_SNOOPING_OPS_pb] = &snooping_remote_ops_pb,
	[(long)SYSFS_SNOOPING_OPS_u32K] = &snooping_remote_ops_u32K,
};

static int setup_special_remote_create(ihk_device_t dev, const struct sysfs_req_create_param *param, struct sysfsm_ops **mopsp, long *cinstancep)
{
	int error;
	struct remote_snooping_param *rsp = NULL;
	long phys = -1;
	struct sysfsm_bitmap_param *pbp = NULL;
	long rpa;

	switch (param->client_ops) {
	case (long)SYSFS_SNOOPING_OPS_d32:
	case (long)SYSFS_SNOOPING_OPS_d64:
	case (long)SYSFS_SNOOPING_OPS_u32:
	case (long)SYSFS_SNOOPING_OPS_u64:
	case (long)SYSFS_SNOOPING_OPS_s:
	case (long)SYSFS_SNOOPING_OPS_pbl:
	case (long)SYSFS_SNOOPING_OPS_pb:
	case (long)SYSFS_SNOOPING_OPS_u32K:
		break;

	default:
		eprintk("mcctrl:setup_special_remote_create:unknown ops %#lx\n", param->client_ops);
		return -EINVAL;
	}

	rsp = kmalloc(sizeof(*rsp), GFP_KERNEL);
	if (!rsp) {
		eprintk("mcctrl:setup_special_remote_create:kmalloc failed.\n");
		return -ENOMEM;
	}

	switch (param->client_ops) {
	case (long)SYSFS_SNOOPING_OPS_s:
	case (long)SYSFS_SNOOPING_OPS_pbl:
	case (long)SYSFS_SNOOPING_OPS_pb:
		phys = ihk_device_map_memory(dev, *cinstancep, sizeof(*pbp));
		pbp = ihk_device_map_virtual(dev, phys, sizeof(*pbp), NULL, 0);
		break;
	}

	rsp->dev = dev;

	switch (param->client_ops) {
	case (long)SYSFS_SNOOPING_OPS_d32:
		rsp->size = sizeof(int);
		rpa = *cinstancep;
		break;

	case (long)SYSFS_SNOOPING_OPS_d64:
		rsp->size = sizeof(long);
		rpa = *cinstancep;
		break;

	case (long)SYSFS_SNOOPING_OPS_u32:
	case (long)SYSFS_SNOOPING_OPS_u32K:
		rsp->size = sizeof(unsigned);
		rpa = *cinstancep;
		break;

	case (long)SYSFS_SNOOPING_OPS_u64:
		rsp->size = sizeof(unsigned long);
		rpa = *cinstancep;
		break;

	case (long)SYSFS_SNOOPING_OPS_s:
	case (long)SYSFS_SNOOPING_OPS_pbl:
	case (long)SYSFS_SNOOPING_OPS_pb:
		rsp->nbits = pbp->nbits;
		rsp->size = (rsp->nbits + 7) / 8;	/* how many bytes */
		rpa = (long)pbp->ptr;
		break;

	default:
		BUG();
	}

	rsp->phys = ihk_device_map_memory(dev, rpa, rsp->size);
	rsp->ptr = ihk_device_map_virtual(dev, rsp->phys, rsp->size, NULL, 0);

	error = 0;
	*mopsp = remote_snooping_ops_table[param->client_ops];
	*cinstancep = (long)rsp;
	rsp = NULL;

#if 0
out:
#endif
	if (pbp) {
		ihk_device_unmap_virtual(dev, pbp, sizeof(*pbp));
		ihk_device_unmap_memory(dev, phys, sizeof(*pbp));
	}
	if (rsp) {
		kfree(rsp);
	}
	return error;
} /* setup_special_remote_create() */

#ifdef MCCTRL_RUST_HELPERS
static int
mcctrl_sysfs_req_is_special_ops(void *ops)
{
	return (((long)SYSFS_SPECIAL_OPS_MIN <= (long)ops)
			&& ((long)ops <= (long)SYSFS_SPECIAL_OPS_MAX));
}

static void *
mcctrl_sysfs_req_os_to_dev_bridge(void *os)
{
	return ihk_os_to_dev(os);
}

static unsigned long
mcctrl_sysfs_req_map_memory_bridge(void *dev, unsigned long rpa,
		unsigned long size)
{
	return ihk_device_map_memory(dev, rpa, size);
}

static void *
mcctrl_sysfs_req_map_virtual_bridge(void *dev, unsigned long pa,
		unsigned long size)
{
	return ihk_device_map_virtual(dev, pa, size, NULL, 0);
}

static void
mcctrl_sysfs_req_unmap_virtual_bridge(void *dev, void *virt,
		unsigned long size)
{
	ihk_device_unmap_virtual(dev, virt, size);
}

static void
mcctrl_sysfs_req_unmap_memory_bridge(void *dev, unsigned long pa,
		unsigned long size)
{
	ihk_device_unmap_memory(dev, pa, size);
}

static void
mcctrl_sysfs_req_wmb_bridge(void)
{
	wmb();
}

static int
mcctrl_sysfs_req_setup_local_bridge(void *os, void *buf,
		unsigned long buf_pa, unsigned long bufsize)
{
	return sysfsm_setup(os, buf, buf_pa, bufsize);
}

static int
mcctrl_sysfs_req_create_local_bridge(void *os,
		struct sysfs_req_create_param *param)
{
	ihk_device_t dev = ihk_os_to_dev(os);
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_ops *ops = &remote_ops;
	long cinstance = param->client_instance;
	struct sysfsm_node *np;
	int error;
	int special = mcctrl_sysfs_req_is_special_ops(
			(void *)param->client_ops);

	if (special) {
		error = setup_special_remote_create(dev, param, &ops,
				&cinstance);
		if (error) {
			return error;
		}
	}

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_create(&udp->sysfsm_data, param->path, param->mode,
			ops, param->client_ops, cinstance);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		if (special) {
			cleanup_special_remote_create(ops, (void *)cinstance);
		}
		return error;
	}

	return 0;
}

static int
mcctrl_sysfs_req_mkdir_local_bridge(void *os,
		struct sysfs_req_mkdir_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_mkdir(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		return error;
	}

	param->handle = (long)np;
	return 0;
}

static int
mcctrl_sysfs_req_symlink_local_bridge(void *os,
		struct sysfs_req_symlink_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_symlink(&udp->sysfsm_data, (void *)param->target,
			param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		return error;
	}

	return 0;
}

static int
mcctrl_sysfs_req_lookup_local_bridge(void *os,
		struct sysfs_req_lookup_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_lookup(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		return error;
	}

	param->handle = (long)np;
	return 0;
}

static int
mcctrl_sysfs_req_unlink_local_bridge(void *os,
		struct sysfs_req_unlink_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	error = sysfsm_unlink(&udp->sysfsm_data, param->path, param->flags);
	if (error) {
		return error;
	}

	return 0;
}
#endif

static void
sysfsm_req_setup(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_setup_body_result(os, param_rpa,
			sizeof(struct sysfs_req_setup_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_setup_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_setup_param *param;
	long buf_pa;
	void *buf;

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	buf_pa = ihk_device_map_memory(dev, param->buf_rpa, param->bufsize);
	buf = ihk_device_map_virtual(dev, buf_pa, param->bufsize, NULL, 0);

	error = sysfsm_setup(os, buf, buf_pa, param->bufsize);

	param->error = error;
	wmb();
	param->busy = 0;

	if (error) {
		ihk_device_unmap_virtual(dev, buf, param->bufsize);
		ihk_device_unmap_memory(dev, buf_pa, param->bufsize);
	}
	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_setup() */

static void
sysfsm_req_create(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_create_body_result(os, param_rpa,
			sizeof(struct sysfs_req_create_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_create_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_create_param *param;
	struct sysfsm_node *np;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_ops *ops;
	long cinstance;

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	ops = &remote_ops;
	cinstance = param->client_instance;
	if (is_special_sysfs_ops((void *)param->client_ops)) {
		error = setup_special_remote_create(dev, param, &ops, &cinstance);
		if (error) {
			goto out;
		}
	}

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_create(&udp->sysfsm_data, param->path, param->mode,
			ops, param->client_ops, cinstance);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		if (is_special_sysfs_ops((void *)param->client_ops)) {
			cleanup_special_remote_create(ops, (void *)cinstance);
		}
		goto out;
	}

	error = 0;

out:
	param->error = error;
	wmb();
	param->busy = 0;

	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_create() */

static void
sysfsm_req_mkdir(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_mkdir_body_result(os, param_rpa,
			sizeof(struct sysfs_req_mkdir_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_mkdir_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_mkdir_param *param;
	struct sysfsm_node *np;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_mkdir(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		goto out;
	}

	error = 0;
	param->handle = (long)np;

out:
	param->error = error;
	wmb();
	param->busy = 0;

	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_mkdir() */

static void
sysfsm_req_symlink(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_symlink_body_result(os, param_rpa,
			sizeof(struct sysfs_req_symlink_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_symlink_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_symlink_param *param;
	struct sysfsm_node *np;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_symlink(&udp->sysfsm_data, (void *)param->target,
			param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		goto out;
	}

	error = 0;
out:
	param->error = error;
	wmb();
	param->busy = 0;

	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_symlink() */

static void
sysfsm_req_lookup(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_lookup_body_result(os, param_rpa,
			sizeof(struct sysfs_req_lookup_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_lookup_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_lookup_param *param;
	struct sysfsm_node *np;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_lookup(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		goto out;
	}

	error = 0;
	param->handle = (long)np;

out:
	param->error = error;
	wmb();
	param->busy = 0;

	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_lookup() */

static void
sysfsm_req_unlink(void *os, long param_rpa)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_req_unlink_body_result(os, param_rpa,
			sizeof(struct sysfs_req_unlink_param),
			mcctrl_sysfs_req_os_to_dev_bridge,
			mcctrl_sysfs_req_map_memory_bridge,
			mcctrl_sysfs_req_map_virtual_bridge,
			mcctrl_sysfs_req_unmap_virtual_bridge,
			mcctrl_sysfs_req_unmap_memory_bridge,
			mcctrl_sysfs_req_unlink_local_bridge,
			mcctrl_sysfs_req_wmb_bridge);
	return;
#else
	int error;
	ihk_device_t dev = ihk_os_to_dev(os);
	long param_pa;
	struct sysfs_req_unlink_param *param;
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);

	param_pa = ihk_device_map_memory(dev, param_rpa, sizeof(*param));
	param = ihk_device_map_virtual(dev, param_pa, sizeof(*param), NULL, 0);

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	error = sysfsm_unlink(&udp->sysfsm_data, param->path, param->flags);
	if (error) {
		goto out;
	}

	error = 0;
out:
	param->error = error;
	wmb();
	param->busy = 0;

	ihk_device_unmap_virtual(dev, param, sizeof(*param));
	ihk_device_unmap_memory(dev, param_pa, sizeof(*param));
	return;
#endif
} /* sysfsm_req_unlink() */

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_sysfs_node_req_bridge(void *node)
{
	struct sysfsm_node *np = node;

	return &np->sdp->sysfs_req;
}

static void
mcctrl_sysfs_complete_req_bridge(void *req0, long result)
{
	struct sysfsm_req *req = req0;

	req->lresult = result;
	wmb();
	req->busy = 0;
	wake_up(&req->wq);
}
#endif

static void
sysfsm_resp_show(void *os, struct sysfsm_node *np, ssize_t ssize)
{
#ifndef MCCTRL_RUST_HELPERS
	struct sysfsm_data *sdp = np->sdp;
	struct sysfsm_req *req = &sdp->sysfs_req;
#endif

	dprintk("mcctrl:sysfsm_resp_show(%p,%s,%ld)\n", os, np->name, ssize);

#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_resp_body_result(np, ssize, mcctrl_sysfs_node_req_bridge,
			mcctrl_sysfs_complete_req_bridge);
#else
	req->lresult = ssize;
	wmb();
	req->busy = 0;
	wake_up(&req->wq);
#endif

	dprintk("mcctrl:sysfsm_resp_show(%p,%s,%ld):\n", os, np->name, ssize);
	return;
} /* sysfsm_resp_show() */

static void
sysfsm_resp_store(void *os, struct sysfsm_node *np, ssize_t ssize)
{
#ifndef MCCTRL_RUST_HELPERS
	struct sysfsm_data *sdp = np->sdp;
	struct sysfsm_req *req = &sdp->sysfs_req;
#endif

	dprintk("mcctrl:sysfsm_resp_store(%p,%s,%ld)\n", os, np->name, ssize);

#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_resp_body_result(np, ssize, mcctrl_sysfs_node_req_bridge,
			mcctrl_sysfs_complete_req_bridge);
#else
	req->lresult = ssize;
	wmb();
	req->busy = 0;
	wake_up(&req->wq);
#endif

	dprintk("mcctrl:sysfsm_resp_store(%p,%s,%ld):\n", os, np->name, ssize);
	return;
} /* sysfsm_resp_store() */

static void
sysfsm_resp_release(void *os, struct sysfsm_node *np, int error)
{
#ifndef MCCTRL_RUST_HELPERS
	struct sysfsm_data *sdp = np->sdp;
	struct sysfsm_req *req = &sdp->sysfs_req;
#endif

	dprintk("mcctrl:sysfsm_resp_release(%p,%p %s,%d)\n",
			os, np, np->name, error);

#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_resp_body_result(np, error, mcctrl_sysfs_node_req_bridge,
			mcctrl_sysfs_complete_req_bridge);
#else
	req->lresult = error;
	wmb();
	req->busy = 0;
	wake_up(&req->wq);
#endif

	dprintk("mcctrl:sysfsm_resp_release(%p,%p,%d):\n", os, np, error);
	return;
} /* sysfsm_resp_release() */

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_sysfs_work_alloc_bridge(unsigned long size)
{
	return kzalloc(size, GFP_ATOMIC);
}

static void
mcctrl_sysfs_work_init_schedule_bridge(void *work0)
{
	struct sysfs_work *work = work0;

	INIT_WORK(&work->work, &sysfsm_work_main);
	schedule_work(&work->work);
}

static void
mcctrl_sysfs_work_alloc_failed_bridge(void)
{
	eprintk("mcctrl:sysfsm_packet_handler:kzalloc failed\n");
}

static void
mcctrl_sysfs_unknown_work_bridge(int msg, void *os, long arg1, long arg2)
{
	wprintk("mcctrl:sysfsm_work_main:unknown work (%d,%p,%#lx,%#lx)\n",
			msg, os, arg1, arg2);
}

static void
mcctrl_sysfs_resp_show_bridge(void *os, void *np, long ssize)
{
	sysfsm_resp_show(os, np, ssize);
}

static void
mcctrl_sysfs_resp_store_bridge(void *os, void *np, long ssize)
{
	sysfsm_resp_store(os, np, ssize);
}

static void
mcctrl_sysfs_resp_release_bridge(void *os, void *np, int error)
{
	sysfsm_resp_release(os, np, error);
}

static void
mcctrl_sysfs_free_work_bridge(void *work)
{
	kfree(work);
}
#endif

static void
sysfsm_work_main(struct work_struct *work0)
{
	struct sysfs_work *work = container_of(work0, struct sysfs_work, work);

#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_work_main_body_result(work,
			sysfsm_req_setup, sysfsm_req_create, sysfsm_req_mkdir,
			sysfsm_req_symlink, sysfsm_req_lookup,
			sysfsm_req_unlink, mcctrl_sysfs_resp_show_bridge,
			mcctrl_sysfs_resp_store_bridge,
			mcctrl_sysfs_resp_release_bridge,
			mcctrl_sysfs_unknown_work_bridge,
			mcctrl_sysfs_free_work_bridge);
#else
	switch (work->msg) {
		case SCD_MSG_SYSFS_REQ_SETUP:
			sysfsm_req_setup(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_REQ_CREATE:
			sysfsm_req_create(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_REQ_MKDIR:
			sysfsm_req_mkdir(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_REQ_SYMLINK:
			sysfsm_req_symlink(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_REQ_LOOKUP:
			sysfsm_req_lookup(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_REQ_UNLINK:
			sysfsm_req_unlink(work->os, work->arg1);
			break;

		case SCD_MSG_SYSFS_RESP_SHOW:
			sysfsm_resp_show(work->os, (void *)work->arg1,
					work->arg2);
			break;

		case SCD_MSG_SYSFS_RESP_STORE:
			sysfsm_resp_store(work->os, (void *)work->arg1,
					work->arg2);
			break;

		case SCD_MSG_SYSFS_RESP_RELEASE:
			sysfsm_resp_release(work->os, (void *)work->arg1,
					work->err);
			break;

		default:
			wprintk("mcctrl:sysfsm_work_main:unknown work (%d,%p,%#lx,%#lx)\n",
					work->msg, work->os, work->arg1, work->arg2);
			break;

	}

	kfree(work);
#endif
	return;
} /* sysfsm_work_main() */

void
sysfsm_packet_handler(void *os, int msg, int err, long arg1, long arg2)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_packet_handler_body_result(os, msg, err, arg1, arg2,
			sizeof(struct sysfs_work),
			mcctrl_sysfs_work_alloc_bridge,
			mcctrl_sysfs_work_init_schedule_bridge,
			mcctrl_sysfs_work_alloc_failed_bridge);
#else
	struct sysfs_work *work = NULL;

	work = kzalloc(sizeof(*work), GFP_ATOMIC);
	if (!work) {
		eprintk("mcctrl:sysfsm_packet_handler:kzalloc failed\n");
		return;
	}

	work->os = os;
	work->msg = msg;
	work->err = err;
	work->arg1 = arg1;
	work->arg2 = arg2;
	INIT_WORK(&work->work, &sysfsm_work_main);

	schedule_work(&work->work);
#endif
	return;
} /* sysfsm_packet_handler() */

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_sysfs_attr_node_bridge(struct attribute *attr)
{
	return container_of(attr, struct sysfsm_node, attr);
}

static void *
mcctrl_sysfs_kobj_node_bridge(struct kobject *kobj)
{
	return container_of(kobj, struct sysfsm_node, kobj);
}

static long
mcctrl_sysfs_node_server_ops_bridge(void *node)
{
	struct sysfsm_node *np = node;

	return (long)np->server_ops;
}
#endif

static ssize_t
sysfsm_show(struct kobject *kobj, struct attribute *attr, char *buf)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)kobj;
	return mcctrl_sysfs_show_body_result(
			mcctrl_sysfs_attr_node_bridge(attr), buf, PAGE_SIZE,
			mcctrl_sysfs_node_server_ops_bridge);
#else
	struct sysfsm_node *np = container_of(attr, struct sysfsm_node, attr);
	ssize_t ssize;

	ssize = -ENOSPC;
	if (np->server_ops && np->server_ops->show) {
		ssize = (*np->server_ops->show)(np->server_ops, np, buf, PAGE_SIZE);
	}

	return ssize;
#endif
} /* sysfsm_show() */

static ssize_t
sysfsm_store(struct kobject *kobj, struct attribute *attr, const char *buf,
		size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)kobj;
	return mcctrl_sysfs_store_body_result(
			mcctrl_sysfs_attr_node_bridge(attr), buf, bufsize,
			mcctrl_sysfs_node_server_ops_bridge);
#else
	struct sysfsm_node *np = container_of(attr, struct sysfsm_node, attr);
	ssize_t ssize;

	ssize = -ENOSPC;
	if (np->server_ops && np->server_ops->store) {
		ssize = (*np->server_ops->store)(np->server_ops, np, buf,
				bufsize);
	}

	return ssize;
#endif
} /* sysfsm_store() */

static void
sysfsm_release(struct kobject *kobj)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_release_body_result(
			mcctrl_sysfs_kobj_node_bridge(kobj),
			mcctrl_sysfs_node_server_ops_bridge);
#else
	struct sysfsm_node *np = container_of(kobj, struct sysfsm_node, kobj);

	if (np->server_ops && np->server_ops->release) {
		(*np->server_ops->release)(np->server_ops, np);
	}
#endif

	return;
} /* sysfsm_release() */

static struct sysfs_ops the_ops = {
	.show =	&sysfsm_show,
	.store = &sysfsm_store,
};

static struct kobj_type the_ktype = {
	.sysfs_ops = &the_ops,
	.release = &sysfsm_release,
};

static struct sysfsm_ops remote_ops = {
	.show = &remote_show,
	.store = &remote_store,
	.release = &remote_release,
};

#ifdef MCCTRL_RUST_HELPERS
static long
mcctrl_sysfs_node_client_ops_bridge(void *instance)
{
	struct sysfsm_node *np = instance;

	return np->client_ops;
}

static long
mcctrl_sysfs_node_client_instance_bridge(void *instance)
{
	struct sysfsm_node *np = instance;

	return np->client_instance;
}

static int
mcctrl_sysfs_node_type_bridge(void *instance)
{
	struct sysfsm_node *np = instance;

	return np->type;
}

static void
mcctrl_sysfs_free_bridge(void *ptr)
{
	kfree(ptr);
}
#endif

static ssize_t
local_show(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	ssize_t ssize;
#else
	struct sysfsm_node *np = instance;
	struct sysfsm_ops *client_ops;
	ssize_t ssize;
#endif

	dprintk("mcctrl:local_show(%p,%p,%p,%#lx)\n",
			ops, instance, buf, bufsize);
#ifdef MCCTRL_RUST_HELPERS
	ssize = mcctrl_sysfs_local_show_body_result(instance, buf, bufsize,
			PAGE_SIZE, mcctrl_sysfs_node_client_ops_bridge,
			mcctrl_sysfs_node_client_instance_bridge);
#else
	client_ops = (void *)np->client_ops;

	ssize = -ENOSPC;
	if (client_ops && client_ops->show) {
		ssize = (*client_ops->show)(client_ops,
				(void *)np->client_instance, buf, PAGE_SIZE);
	}
#endif

	dprintk("mcctrl:local_show(%p,%p,%p,%#lx): %ld\n",
			ops, instance, buf, bufsize, ssize);
	return ssize;
} /* local_show() */

static ssize_t
local_store(struct sysfsm_ops *ops, void *instance, const void *buf,
		size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	ssize_t ssize;
#else
	struct sysfsm_node *np = instance;
	struct sysfsm_ops *client_ops;
	ssize_t ssize;
#endif

	dprintk("mcctrl:local_store(%p,%p,%p,%#lx)\n",
			ops, instance, buf, bufsize);
#ifdef MCCTRL_RUST_HELPERS
	ssize = mcctrl_sysfs_local_store_body_result(instance, buf, bufsize,
			mcctrl_sysfs_node_client_ops_bridge,
			mcctrl_sysfs_node_client_instance_bridge);
#else
	client_ops = (void *)np->client_ops;

	ssize = -ENOSPC;
	if (client_ops && client_ops->store) {
		ssize = (*client_ops->store)(client_ops,
				(void *)np->client_instance, buf, bufsize);
	}
#endif

	dprintk("mcctrl:local_store(%p,%p,%p,%#lx): %ld\n",
			ops, instance, buf, bufsize, ssize);
	return ssize;
} /* local_store() */

static void
local_release(struct sysfsm_ops *ops, void *instance)
{
#ifndef MCCTRL_RUST_HELPERS
	struct sysfsm_node *np = instance;
	struct sysfsm_ops *client_ops;
#endif

	dprintk("mcctrl:local_release(%p,%p)\n", ops, instance);
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_local_release_body_result(instance, SNT_FILE,
			mcctrl_sysfs_node_type_bridge,
			mcctrl_sysfs_node_client_ops_bridge,
			mcctrl_sysfs_node_client_instance_bridge);
#else
	client_ops = (void *)np->client_ops;

	if ((np->type == SNT_FILE) && client_ops && client_ops->release) {
		(*client_ops->release)(client_ops,
				(void *)np->client_instance);
	}
#endif

	dprintk("mcctrl:local_release(%p,%p):\n", ops, instance);
	return;
} /* local_release() */

static struct sysfsm_ops local_ops = {
	.show = &local_show,
	.store = &local_store,
	.release = &local_release,
};

/***********************************************************************
 * local snooping
 */
static void cleanup_special_local_create(struct sysfsm_ops *ops, void *instance)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_sysfs_cleanup_special_local_create_body_result(instance,
			mcctrl_sysfs_free_bridge);
#else
	kfree(instance);
#endif
	return;
} /* cleanup_special_local_create() */


/**** local int ****/
static ssize_t snooping_local_show_d32(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_i32_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%d\n", *(int *)instance);
#endif
} /* snooping_local_show_d32() */

struct sysfsm_ops snooping_local_ops_d32 = {
	.show = &snooping_local_show_d32,
};

/**** local long ****/
static ssize_t snooping_local_show_d64(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_i64_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%ld\n", *(long *)instance);
#endif
} /* snooping_local_show_d64() */

struct sysfsm_ops snooping_local_ops_d64 = {
	.show = &snooping_local_show_d64,
};

/**** local unsigned ****/
static ssize_t snooping_local_show_u32(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_u32_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%u\n", *(unsigned *)instance);
#endif
} /* snooping_local_show_u32() */

struct sysfsm_ops snooping_local_ops_u32 = {
	.show = &snooping_local_show_u32,
};

/**** local unsigned long ****/
static ssize_t snooping_local_show_u64(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_u64_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%lu\n", *(unsigned long *)instance);
#endif
} /* snooping_local_show_u64() */

struct sysfsm_ops snooping_local_ops_u64 = {
	.show = &snooping_local_show_u64,
};

/**** local string ****/
static ssize_t snooping_local_show_s(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_string_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%s\n", (char *)instance);
#endif
} /* snooping_local_show_s() */

struct sysfsm_ops snooping_local_ops_s = {
	.show = &snooping_local_show_s,
};

/**** local list ****/
#ifdef MCCTRL_RUST_HELPERS
static unsigned long mcctrl_sysfs_bitmap_scnlistprintf_bridge(void *buf,
		unsigned long bufsize, void *ptr, int nbits)
{
	return bitmap_scnlistprintf(buf, bufsize, ptr, nbits);
}
#endif

static ssize_t snooping_local_show_pbl(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_bitmap_body_result(instance, buf,
			bufsize, mcctrl_sysfs_bitmap_scnlistprintf_bridge);
#else
	size_t ret;
	const struct sysfsm_bitmap_param *p = instance;

	ret = bitmap_scnlistprintf(buf, bufsize, p->ptr, p->nbits);
	if (ret < bufsize - 1) {
		sprintf(buf + ret, "\n");
		return ret + 1;
	}

	return 0;
#endif
} /* snooping_local_show_pbl() */

struct sysfsm_ops snooping_local_ops_pbl = {
	.show = &snooping_local_show_pbl,
	.release = &cleanup_special_local_create,
};

/**** local map ****/
#ifdef MCCTRL_RUST_HELPERS
static unsigned long mcctrl_sysfs_bitmap_scnprintf_bridge(void *buf,
		unsigned long bufsize, void *ptr, int nbits)
{
	return bitmap_scnprintf(buf, bufsize, ptr, nbits);
}
#endif

static ssize_t snooping_local_show_pb(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_bitmap_body_result(instance, buf,
			bufsize, mcctrl_sysfs_bitmap_scnprintf_bridge);
#else
	size_t ret;
	const struct sysfsm_bitmap_param *p = instance;

	ret = bitmap_scnprintf(buf, bufsize, p->ptr, p->nbits);
	if (ret < bufsize - 1) {
		sprintf(buf + ret, "\n");
		return ret + 1;
	}

	return 0;
#endif
} /* snooping_local_show_pb() */

struct sysfsm_ops snooping_local_ops_pb = {
	.show = &snooping_local_show_pb,
	.release = &cleanup_special_local_create,
};

/**** local K unsigned ****/
static ssize_t snooping_local_show_u32K(struct sysfsm_ops *ops, void *instance, void *buf, size_t bufsize)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)ops;
	return mcctrl_sysfs_snooping_show_u32k_body_result(instance, buf,
			bufsize);
#else
	return sprintf(buf, "%uK\n", (*(unsigned *)instance >> 10));
#endif
} /* snooping_local_show_u32K() */

struct sysfsm_ops snooping_local_ops_u32K = {
	.show = &snooping_local_show_u32K,
};

struct sysfsm_ops * const local_snooping_ops_table[] = {
	[(long)SYSFS_SNOOPING_OPS_d32] = &snooping_local_ops_d32,
	[(long)SYSFS_SNOOPING_OPS_d64] = &snooping_local_ops_d64,
	[(long)SYSFS_SNOOPING_OPS_u32] = &snooping_local_ops_u32,
	[(long)SYSFS_SNOOPING_OPS_u64] = &snooping_local_ops_u64,
	[(long)SYSFS_SNOOPING_OPS_s] = &snooping_local_ops_s,
	[(long)SYSFS_SNOOPING_OPS_pbl] = &snooping_local_ops_pbl,
	[(long)SYSFS_SNOOPING_OPS_pb] = &snooping_local_ops_pb,
	[(long)SYSFS_SNOOPING_OPS_u32K] = &snooping_local_ops_u32K,
};

#ifdef MCCTRL_RUST_HELPERS
static void *
mcctrl_sysfs_local_alloc_bridge(unsigned long size)
{
	return kmalloc(size, GFP_KERNEL);
}

static void
mcctrl_sysfs_local_copy_bridge(void *dst, const void *src, unsigned long size)
{
	memcpy(dst, src, size);
}

static void
mcctrl_sysfs_unknown_local_ops_bridge(long client_ops)
{
	eprintk("mcctrl:setup_special_local_create:unknown ops %#lx\n",
			client_ops);
}
#endif

#ifdef MCCTRL_RUST_HELPERS
static void
mcctrl_sysfs_setup_special_failed_bridge(int error)
{
	eprintk("mcctrl:sysfsm_createf:setup_special_local_create failed. %d\n",
			error);
}
#else
static int setup_special_local_create(struct sysfs_req_create_param *param)
{
	struct sysfsm_bitmap_param *p = NULL;

	switch (param->client_ops) {
	case (long)SYSFS_SNOOPING_OPS_d32:
	case (long)SYSFS_SNOOPING_OPS_d64:
	case (long)SYSFS_SNOOPING_OPS_u32:
	case (long)SYSFS_SNOOPING_OPS_u64:
	case (long)SYSFS_SNOOPING_OPS_s:
	case (long)SYSFS_SNOOPING_OPS_u32K:
		param->client_ops = (long)local_snooping_ops_table[param->client_ops];
		return 0;

	case (long)SYSFS_SNOOPING_OPS_pbl:
	case (long)SYSFS_SNOOPING_OPS_pb:
		p = kmalloc(sizeof(*p), GFP_KERNEL);
		if (!p) {
			return -ENOMEM;
		}

		memcpy(p, (void *)param->client_instance, sizeof(*p));

		param->client_ops = (long)local_snooping_ops_table[param->client_ops];
		param->client_instance = (long)p;
		return 0;
	}

	eprintk("mcctrl:setup_special_local_create:unknown ops %#lx\n", param->client_ops);
	return -EINVAL;
} /* setup_special_local_create() */
#endif

#ifdef MCCTRL_RUST_HELPERS
static int
mcctrl_sysfs_local_create_bridge(void *os, struct sysfs_req_create_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_create(&udp->sysfsm_data, param->path, param->mode,
			&local_ops, param->client_ops, param->client_instance);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_createf:sysfsm_create failed. %d\n",
				error);
		return error;
	}

	return 0;
}

static void
mcctrl_sysfs_cleanup_special_local_create_bridge(void *ops, void *instance)
{
	cleanup_special_local_create((struct sysfsm_ops *)ops, instance);
}

static int
mcctrl_sysfs_mkdir_local_bridge(void *os, struct sysfs_req_mkdir_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_mkdir(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_mkdirf:sysfsm_mkdir failed. %d\n",
				error);
		return error;
	}

	param->handle = (long)np;
	return 0;
}

static int
mcctrl_sysfs_symlink_local_bridge(void *os,
		struct sysfs_req_symlink_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_symlink(&udp->sysfsm_data, (void *)param->target,
			param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_symlinkf:sysfsm_symlink failed. %d\n",
				error);
		return error;
	}

	return 0;
}

static int
mcctrl_sysfs_lookup_local_bridge(void *os,
		struct sysfs_req_lookup_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	np = sysfsm_lookup(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_lookupf:sysfsm_lookup failed. %d\n",
				error);
		return error;
	}

	param->handle = (long)np;
	return 0;
}

static int
mcctrl_sysfs_unlink_local_bridge(void *os,
		struct sysfs_req_unlink_param *param)
{
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	int error;

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n", __func__);
		return -EINVAL;
	}

	error = sysfsm_unlink(&udp->sysfsm_data, param->path, param->flags);
	if (error) {
		eprintk("mcctrl:sysfsm_unlinkf:sysfsm_unlink failed. %d\n",
				error);
		return error;
	}

	return 0;
}

#endif

int
sysfsm_createf(ihk_os_t os, struct sysfsm_ops *ops, void *instance, int mode,
		const char *fmt, ...)
{
	int error;
#ifndef MCCTRL_RUST_HELPERS
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
	char special = 0;
#endif
	va_list ap;
	ssize_t n;
	struct sysfs_req_create_param *param = NULL;

	dprintk("mcctrl:sysfsm_createf(%p,%p,%p,%#o,%s,...)\n",
			os, ops, instance, mode, fmt);

	param = (void *)__get_free_page(GFP_KERNEL);
	if (!param) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_createf:__get_free_page failed. %d\n",
				error);
		goto out;
	}

	param->client_ops = (long)ops;
	param->client_instance = (long)instance;
	param->mode = mode;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	error = mcctrl_sysfs_path_error(param->path, n, sizeof(param->path));
	if (error == -ENAMETOOLONG) {
		eprintk("mcctrl:sysfsm_createf:vsnprintf failed. %d\n", error);
		goto out;
	}
	dprintk("mcctrl:sysfsm_createf:path %s\n", param->path);
	if (error == -ENOENT) {
		eprintk("mcctrl:sysfsm_createf:not an absolute path. %d\n",
				error);
		goto out;
	}

#ifdef MCCTRL_RUST_HELPERS
	error = mcctrl_sysfs_createf_post_path_body_result(os, param,
			(void * const *)local_snooping_ops_table,
			sizeof(struct sysfsm_bitmap_param),
			mcctrl_sysfs_local_alloc_bridge,
			mcctrl_sysfs_local_copy_bridge,
			mcctrl_sysfs_unknown_local_ops_bridge,
			mcctrl_sysfs_local_create_bridge,
			mcctrl_sysfs_cleanup_special_local_create_bridge,
			mcctrl_sysfs_setup_special_failed_bridge);
	goto out;
#else
	if (is_special_sysfs_ops((void *)param->client_ops)) {
		error = setup_special_local_create(param);
		if (error) {
			eprintk("mcctrl:sysfsm_createf:setup_special_local_create failed. %d\n", error);
			goto out;
		}
		special = 1;
	}

	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_create(&udp->sysfsm_data, param->path, param->mode, &local_ops,
			param->client_ops, param->client_instance);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_createf:sysfsm_create failed. %d\n", error);
		goto out;
	}

	error = 0;
#endif
out:
#ifndef MCCTRL_RUST_HELPERS
	if (error && special) {
		cleanup_special_local_create((void *)param->client_ops, (void *)param->client_instance);
	}
#endif
	free_page((uintptr_t)param);
	if (error) {
		eprintk("mcctrl:sysfsm_createf(%p,%p,%p,%#o,%s,...): %d\n",
				os, ops, instance, mode, fmt, error);
	}
	dprintk("mcctrl:sysfsm_createf(%p,%p,%p,%#o,%s,...): %d\n",
			os, ops, instance, mode, fmt, error);
	return error;
} /* sysfsm_createf() */

int
sysfsm_mkdirf(ihk_os_t os, sysfs_handle_t *dirhp, const char *fmt, ...)
{
	int error;
#ifndef MCCTRL_RUST_HELPERS
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
#endif
	struct sysfs_req_mkdir_param *param = NULL;
	va_list ap;
	int n;

	dprintk("mcctrl:sysfsm_mkdirf(%p,%p,%s,...)\n", os, dirhp, fmt);

	param = (void *)__get_free_page(GFP_KERNEL);
	if (!param) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_mkdirf:__get_free_page failed. %d\n",
				error);
		goto out;
	}

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	error = mcctrl_sysfs_path_error(param->path, n, sizeof(param->path));
	if (error == -ENAMETOOLONG) {
		eprintk("mcctrl:sysfsm_mkdirf:vsnprintf failed. %d\n", error);
		goto out;
	}
	dprintk("mcctrl:sysfsm_mkdirf:path %s\n", param->path);
	if (error == -ENOENT) {
		eprintk("mcctrl:sysfsm_mkdirf:not an absolute path. %d\n",
				error);
		goto out;
	}

#ifdef MCCTRL_RUST_HELPERS
	error = mcctrl_sysfs_mkdirf_post_path_body_result(os, param,
			mcctrl_sysfs_mkdir_local_bridge);
	if (!error && dirhp) {
		dirhp->handle = param->handle;
	}
	goto out;
#else
	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_mkdir(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_mkdirf:sysfsm_mkdir failed. %d\n",
				error);
		goto out;
	}

	error = 0;
	if (dirhp) {
		dirhp->handle = (long)np;
	}
#endif

out:
	free_page((uintptr_t)param);
	if (error) {
		eprintk("mcctrl:sysfsm_mkdirf(%p,%p,%s,...): %d\n",
				os, dirhp, fmt, error);
	}
	dprintk("mcctrl:sysfsm_mkdirf(%p,%p,%s,...): %d %#lx\n", os, dirhp,
			fmt, error, (dirhp)?dirhp->handle:0);
	return error;
} /* sysfsm_mkdirf() */

int
sysfsm_symlinkf(ihk_os_t os, sysfs_handle_t targeth, const char *fmt, ...)
{
	int error;
#ifndef MCCTRL_RUST_HELPERS
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
#endif
	struct sysfs_req_symlink_param *param = NULL;
	va_list ap;
	int n;

	dprintk("mcctrl:sysfsm_symlinkf(%p,%#lx,%s,...)\n",
			os, targeth.handle, fmt);

	param = (void *)__get_free_page(GFP_KERNEL);
	if (!param) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_symlinkf:__get_free_page failed. %d\n",
				error);
		goto out;
	}

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	error = mcctrl_sysfs_path_error(param->path, n, sizeof(param->path));
	if (error == -ENAMETOOLONG) {
		eprintk("mcctrl:sysfsm_symlinkf:vsnprintf failed. %d\n", error);
		goto out;
	}
	dprintk("mcctrl:sysfsm_symlinkf:path %s\n", param->path);
	if (error == -ENOENT) {
		eprintk("mcctrl:sysfsm_symlinkf:not an absolute path. %d\n",
				error);
		goto out;
	}

#ifdef MCCTRL_RUST_HELPERS
	param->target = targeth.handle;
	error = mcctrl_sysfs_symlinkf_post_path_body_result(os, param,
			mcctrl_sysfs_symlink_local_bridge);
	goto out;
#else
	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_symlink(&udp->sysfsm_data, (void *)targeth.handle,
			param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_symlinkf:sysfsm_symlink failed. %d\n",
				error);
		goto out;
	}

	error = 0;
#endif
out:
	free_page((uintptr_t)param);
	if (error) {
		eprintk("mcctrl:sysfsm_symlinkf(%p,%#lx,%s,...): %d\n",
				os, targeth.handle, fmt, error);
	}
	dprintk("mcctrl:sysfsm_symlinkf(%p,%#lx,%s,...): %d\n",
			os, targeth.handle, fmt, error);
	return error;
} /* sysfsm_symlinkf() */

int
sysfsm_lookupf(ihk_os_t os, sysfs_handle_t *objhp, const char *fmt, ...)
{
	int error;
#ifndef MCCTRL_RUST_HELPERS
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
	struct sysfsm_node *np;
#endif
	struct sysfs_req_lookup_param *param = NULL;
	va_list ap;
	int n;

	dprintk("mcctrl:sysfsm_lookupf(%p,%p,%s,...)\n", os, objhp, fmt);

	param = (void *)__get_free_page(GFP_KERNEL);
	if (!param) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_lookupf:__get_free_page failed. %d\n",
				error);
		goto out;
	}

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	error = mcctrl_sysfs_path_error(param->path, n, sizeof(param->path));
	if (error == -ENAMETOOLONG) {
		eprintk("mcctrl:sysfsm_lookupf:vsnprintf failed. %d\n", error);
		goto out;
	}
	dprintk("mcctrl:sysfsm_lookupf:path %s\n", param->path);
	if (error == -ENOENT) {
		eprintk("mcctrl:sysfsm_lookupf:not an absolute path. %d\n",
				error);
		goto out;
	}

#ifdef MCCTRL_RUST_HELPERS
	error = mcctrl_sysfs_lookupf_post_path_body_result(os, param,
			mcctrl_sysfs_lookup_local_bridge);
	if (!error && objhp) {
		objhp->handle = param->handle;
	}
	goto out;
#else
	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	np = sysfsm_lookup(&udp->sysfsm_data, param->path);
	if (IS_ERR(np)) {
		error = PTR_ERR(np);
		eprintk("mcctrl:sysfsm_lookupf:sysfsm_lookup failed. %d\n",
				error);
		goto out;
	}

	error = 0;
	if (objhp) {
		objhp->handle = (long)np;
	}
#endif

out:
	free_page((uintptr_t)param);
	if (error) {
		eprintk("mcctrl:sysfsm_lookupf(%p,%p,%s,...): %d\n",
				os, objhp, fmt, error);
	}
	dprintk("mcctrl:sysfsm_lookupf(%p,%p,%s,...): %d %#lx\n", os, objhp,
			fmt, error, (objhp)?objhp->handle:0);
	return error;
} /* sysfsm_lookupf() */

int
sysfsm_unlinkf(ihk_os_t os, int flags, const char *fmt, ...)
{
	int error;
#ifndef MCCTRL_RUST_HELPERS
	struct mcctrl_usrdata *udp = ihk_host_os_get_usrdata(os);
#endif
	struct sysfs_req_unlink_param *param = NULL;
	va_list ap;
	int n;

	dprintk("mcctrl:sysfsm_unlinkf(%p,%#x,%s,...)\n", os, flags, fmt);

	param = (void *)__get_free_page(GFP_KERNEL);
	if (!param) {
		error = -ENOMEM;
		eprintk("mcctrl:sysfsm_unlinkf:__get_free_page failed. %d\n",
				error);
		goto out;
	}

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	error = mcctrl_sysfs_path_error(param->path, n, sizeof(param->path));
	if (error == -ENAMETOOLONG) {
		eprintk("mcctrl:sysfsm_unlinkf:vsnprintf failed. %d\n", error);
		goto out;
	}
	dprintk("mcctrl:sysfsm_unlinkf:path %s\n", param->path);
	if (error == -ENOENT) {
		eprintk("mcctrl:sysfsm_unlinkf:not an absolute path. %d\n",
				error);
		goto out;
	}

#ifdef MCCTRL_RUST_HELPERS
	param->flags = flags;
	error = mcctrl_sysfs_unlinkf_post_path_body_result(os, param,
			mcctrl_sysfs_unlink_local_bridge);
	goto out;
#else
	if (!udp) {
		pr_err("%s: error: mcctrl_usrdata not found\n",
			 __func__);
		error = -EINVAL;
		goto out;
	}

	error = sysfsm_unlink(&udp->sysfsm_data, param->path, flags);
	if (error) {
		eprintk("mcctrl:sysfsm_unlinkf:sysfsm_unlink failed. %d\n",
				error);
		goto out;
	}

	error = 0;
#endif
out:
	free_page((uintptr_t)param);
	if (error) {
		eprintk("mcctrl:sysfsm_unlinkf(%p,%#x,%s,...): %d\n",
				os, flags, fmt, error);
	}
	dprintk("mcctrl:sysfsm_unlinkf(%p,%#x,%s,...): %d\n",
			os, flags, fmt, error);
	return error;
} /* sysfsm_unlinkf() */

/**** End of File ****/
