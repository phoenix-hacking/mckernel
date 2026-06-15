/**
 * \file sysfs.c
 *  License details are found in the file LICENSE.
 * \brief
 *  sysfs framework, IHK-Slave side
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2015  RIKEN AICS
 */
/*
 * HISTORY:
 */

#include <ihk/mm.h>
#include <ihk/types.h>
#include <ikc/queue.h>
#include <cls.h>
#include <kmsg.h>
#include <kmalloc.h>
#include <page.h>
#include <string.h>
#include <stdarg.h>
#include <arch/cpu.h>
#include <sysfs.h>
#include <sysfs_msg.h>
#include <vsprintf.h>
#include <ihk/debug.h>
#include <object_helpers.h>

static size_t sysfs_data_bufsize;
static void *sysfs_data_buf;

#ifndef MCKERNEL_RUST_OBJECT_HELPERS
int
is_special_sysfs_ops(void *ops)
{
	return (((long)SYSFS_SPECIAL_OPS_MIN <= (long)ops)
			&& ((long)ops <= (long)SYSFS_SPECIAL_OPS_MAX));
}
#endif /* MCKERNEL_RUST_OBJECT_HELPERS */

static ssize_t
sysfss_show_bridge(void *ops0, void *instance, void *buf, size_t bufsize)
{
	struct sysfs_ops *ops = ops0;

	return ops->show(ops, instance, buf, bufsize);
}

static ssize_t
sysfss_store_bridge(void *ops0, void *instance, void *buf, size_t size)
{
	struct sysfs_ops *ops = ops0;

	return ops->store(ops, instance, buf, size);
}

static void
sysfss_release_bridge(void *ops0, void *instance)
{
	struct sysfs_ops *ops = ops0;

	ops->release(ops, instance);
}

static int
sysfss_send_bridge(int msg, int err, long arg1, long arg2)
{
	struct ikc_scd_packet packet;
	int prep_rc;

	prep_rc = sysfss_packet_prepare_result(&packet, msg, err, arg1,
			arg2);
	if (prep_rc)
		return prep_rc;
	return ihk_ikc_send(get_this_cpu_local_var()->ikc2linux, &packet, 0);
}

static int
sysfs_request_send_bridge(int msg, long arg1)
{
	struct ikc_scd_packet packet;
	int prep_rc;

	prep_rc = sysfs_request_packet_prepare_result(&packet, msg, arg1);
	if (prep_rc)
		return prep_rc;
	return ihk_ikc_send(get_this_cpu_local_var()->ikc2linux, &packet, 0);
}

static void
sysfs_request_pause_bridge(void)
{
	cpu_pause();
}

static void
sysfs_request_barrier_bridge(void)
{
	rmb();
}

static void *
sysfs_init_alloc_bridge(int npages, unsigned long flags)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

static void
sysfs_init_free_bridge(void *addr, int npages)
{
	_ihk_mc_free_pages(addr, npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

static long
sysfs_init_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

static void sysfss_req_show_log_bridge(int event, long nodeh, void *ops,
		void *instance, size_t size, int error, int packet_err,
		ssize_t ssize);
static void sysfss_req_store_log_bridge(int event, long nodeh, void *ops,
		void *instance, size_t size, int error, int packet_err,
		ssize_t ssize);
static void sysfss_req_release_log_bridge(int event, long nodeh, void *ops,
		void *instance, size_t size, int error, int packet_err,
		ssize_t ssize);
static void sysfs_public_request_log_bridge(int event, int msg, int error);

static int setup_special_create(struct sysfs_req_create_param *param, struct sysfs_bitmap_param *pbp)
{
	int error;

	error = sysfs_setup_special_create_result(param, pbp,
			sysfs_init_phys_bridge);
	if (!error) {
		return 0;
	}
	ekprintf("setup_special_create:unknown ops %#lx\n", param->client_ops);
	return error;
} /* setup_special_create() */

int
sysfs_createf(struct sysfs_ops *ops, void *instance, int mode,
		const char *fmt, ...)
{
	int error;
	va_list ap;
	ssize_t n;
	struct sysfs_req_create_param *param = NULL;
	struct sysfs_bitmap_param asbp;

	dkprintf("sysfs_createf(%p,%p,%#o,%s,...)\n",
			ops, instance, mode, fmt);

	param = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_createf:allocate_pages failed. %d\n", error);
		goto out;
	}

	param->client_ops = (long)ops;
	param->client_instance = (long)instance;
	param->mode = mode;
	param->busy = 1;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	dkprintf("sysfs_createf:path %s\n", param->path);
	error = sysfs_path_error_result(n, param->path[0] == '/',
			sizeof(param->path));
	if (error) {
		if (error == -ENAMETOOLONG) {
			ekprintf("sysfs_createf:vsnprintf failed. %d\n", error);
		}
		else {
			ekprintf("sysfs_createf:not an absolute path. %d\n", error);
		}
		goto out;
	}

	if (is_special_sysfs_ops(ops)) {
		error = setup_special_create(param, &asbp);
		if (error) {
			ekprintf("sysfs_createf:setup_special_create failed. %d\n", error);
			goto out;
		}
	}

	error = sysfs_request_logged_result(SCD_MSG_SYSFS_REQ_CREATE, param,
			virt_to_phys(param), sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			NULL, sysfs_public_request_log_bridge, NULL);
	if (error) {
		goto out;
	}

out:
	if (param) {
		_ihk_mc_free_pages(param, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (error) {
		ekprintf("sysfs_createf(%p,%p,%#o,%s,...): %d\n",
				ops, instance, mode, fmt, error);
	}
	dkprintf("sysfs_createf(%p,%p,%#o,%s,...): %d\n",
			ops, instance, mode, fmt, error);
	return error;
} /* sysfs_createf() */

int
sysfs_mkdirf(sysfs_handle_t *dirhp, const char *fmt, ...)
{
	int error;
	struct sysfs_req_mkdir_param *param = NULL;
	va_list ap;
	int n;

	dkprintf("sysfs_mkdirf(%p,%s,...)\n", dirhp, fmt);

	param = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_mkdirf:allocate_pages failed. %d\n", error);
		goto out;
	}

	param->busy = 1;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	dkprintf("sysfs_mkdirf:path %s\n", param->path);
	error = sysfs_path_error_result(n, param->path[0] == '/',
			sizeof(param->path));
	if (error) {
		if (error == -ENAMETOOLONG) {
			ekprintf("sysfs_mkdirf:vsnprintf failed. %d\n", error);
		}
		else {
			ekprintf("sysfs_mkdirf:not an absolute path. %d\n", error);
		}
		goto out;
	}

	error = sysfs_request_logged_result(SCD_MSG_SYSFS_REQ_MKDIR, param,
			virt_to_phys(param), sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			(long *)dirhp, sysfs_public_request_log_bridge, NULL);
	if (error) {
		goto out;
	}

out:
	if (param) {
		_ihk_mc_free_pages(param, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (error) {
		ekprintf("sysfs_mkdirf(%p,%s,...): %d\n", dirhp, fmt, error);
	}
	dkprintf("sysfs_mkdirf(%p,%s,...): %d %#lx\n", dirhp, fmt, error,
			(dirhp)?dirhp->handle:0);
	return error;
} /* sysfs_mkdirf() */

int
sysfs_symlinkf(sysfs_handle_t targeth, const char *fmt, ...)
{
	int error;
	struct sysfs_req_symlink_param *param = NULL;
	va_list ap;
	int n;

	dkprintf("sysfs_symlinkf(%#lx,%s,...)\n", targeth.handle, fmt);

	param = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_symlinkf:allocate_pages failed. %d\n", error);
		goto out;
	}

	param->target = targeth.handle;
	param->busy = 1;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	dkprintf("sysfs_symlinkf:path %s\n", param->path);
	error = sysfs_path_error_result(n, param->path[0] == '/',
			sizeof(param->path));
	if (error) {
		if (error == -ENAMETOOLONG) {
			ekprintf("sysfs_symlinkf:vsnprintf failed. %d\n", error);
		}
		else {
			ekprintf("sysfs_symlinkf:not an absolute path. %d\n", error);
		}
		goto out;
	}

	error = sysfs_request_logged_result(SCD_MSG_SYSFS_REQ_SYMLINK, param,
			virt_to_phys(param), sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			NULL, sysfs_public_request_log_bridge, NULL);
	if (error) {
		goto out;
	}

out:
	if (param) {
		_ihk_mc_free_pages(param, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (error) {
		ekprintf("sysfs_symlinkf(%#lx,%s,...): %d\n",
				targeth.handle, fmt, error);
	}
	dkprintf("sysfs_symlinkf(%#lx,%s,...): %d\n",
			targeth.handle, fmt, error);
	return error;
} /* sysfs_symlinkf() */

int
sysfs_lookupf(sysfs_handle_t *objhp, const char *fmt, ...)
{
	int error;
	struct sysfs_req_lookup_param *param = NULL;
	va_list ap;
	int n;

	dkprintf("sysfs_lookupf(%p,%s,...)\n", objhp, fmt);

	param = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_lookupf:allocate_pages failed. %d\n", error);
		goto out;
	}

	param->busy = 1;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	dkprintf("sysfs_lookupf:path %s\n", param->path);
	error = sysfs_path_error_result(n, param->path[0] == '/',
			sizeof(param->path));
	if (error) {
		if (error == -ENAMETOOLONG) {
			ekprintf("sysfs_lookupf:vsnprintf failed. %d\n", error);
		}
		else {
			ekprintf("sysfs_lookupf:not an absolute path. %d\n", error);
		}
		goto out;
	}

	error = sysfs_request_logged_result(SCD_MSG_SYSFS_REQ_LOOKUP, param,
			virt_to_phys(param), sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			(long *)objhp, sysfs_public_request_log_bridge, NULL);
	if (error) {
		goto out;
	}

out:
	if (param) {
		_ihk_mc_free_pages(param, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (error) {
		ekprintf("sysfs_lookupf(%p,%s,...): %d\n", objhp, fmt, error);
	}
	dkprintf("sysfs_lookupf(%p,%s,...): %d %#lx\n", objhp, fmt, error,
			(objhp)?objhp->handle:0);
	return error;
} /* sysfs_lookupf() */

int
sysfs_unlinkf(int flags, const char *fmt, ...)
{
	int error;
	struct sysfs_req_unlink_param *param = NULL;
	va_list ap;
	int n;

	dkprintf("sysfs_unlinkf(%#x,%s,...)\n", flags, fmt);

	param = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_unlinkf:allocate_pages failed. %d\n", error);
		goto out;
	}

	param->flags = flags;
	param->busy = 1;

	va_start(ap, fmt);
	n = vsnprintf(param->path, sizeof(param->path), fmt, ap);
	va_end(ap);
	dkprintf("sysfs_unlinkf:path %s\n", param->path);
	error = sysfs_path_error_result(n, param->path[0] == '/',
			sizeof(param->path));
	if (error) {
		if (error == -ENAMETOOLONG) {
			ekprintf("sysfs_unlinkf:vsnprintf failed. %d\n", error);
		}
		else {
			ekprintf("sysfs_unlinkf:not an absolute path. %d\n", error);
		}
		goto out;
	}

	error = sysfs_request_logged_result(SCD_MSG_SYSFS_REQ_UNLINK, param,
			virt_to_phys(param), sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			NULL, sysfs_public_request_log_bridge, NULL);
	if (error) {
		goto out;
	}

out:
	if (param) {
		_ihk_mc_free_pages(param, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (error) {
		ekprintf("sysfs_unlinkf(%#x,%s,...): %d\n", flags, fmt, error);
	}
	dkprintf("sysfs_unlinkf(%#x,%s,...): %d\n", flags, fmt, error);
	return error;
} /* sysfs_unlinkf() */

static void
sysfs_public_request_log_bridge(int event, int msg, int error)
{
	if (event == SYSFS_REQUEST_LOG_SEND_ERROR) {
		switch (msg) {
		case SCD_MSG_SYSFS_REQ_CREATE:
			ekprintf("sysfs_createf:ihk_ikc_send failed. %d\n",
					error);
			break;
		case SCD_MSG_SYSFS_REQ_MKDIR:
			ekprintf("sysfs_mkdirf:ihk_ikc_send failed. %d\n",
					error);
			break;
		case SCD_MSG_SYSFS_REQ_SYMLINK:
			ekprintf("sysfs_symlinkf:ihk_ikc_send failed. %d\n",
					error);
			break;
		case SCD_MSG_SYSFS_REQ_LOOKUP:
			ekprintf("sysfs_lookupf:ihk_ikc_send failed. %d\n",
					error);
			break;
		case SCD_MSG_SYSFS_REQ_UNLINK:
			ekprintf("sysfs_unlinkf:ihk_ikc_send failed. %d\n",
					error);
			break;
		default:
			break;
		}
	}
	else if (event == SYSFS_REQUEST_LOG_RESPONSE_ERROR) {
		switch (msg) {
		case SCD_MSG_SYSFS_REQ_CREATE:
			ekprintf("sysfs_createf:SCD_MSG_SYSFS_REQ_CREATE"
					" failed. %d\n", error);
			break;
		case SCD_MSG_SYSFS_REQ_MKDIR:
			ekprintf("sysfs_mkdirf:SCD_MSG_SYSFS_REQ_MKDIR"
					" failed. %d\n", error);
			break;
		case SCD_MSG_SYSFS_REQ_SYMLINK:
			ekprintf("sysfs_symlinkf:"
					"SCD_MSG_SYSFS_REQ_SYMLINK failed."
					" %d\n", error);
			break;
		case SCD_MSG_SYSFS_REQ_LOOKUP:
			ekprintf("sysfs_lookupf:SCD_MSG_SYSFS_REQ_LOOKUP"
					" failed. %d\n", error);
			break;
		case SCD_MSG_SYSFS_REQ_UNLINK:
			ekprintf("sysfs_unlinkf:SCD_MSG_SYSFS_REQ_UNLINK"
					" failed. %d\n", error);
			break;
		default:
			break;
		}
	}
}

static void
sysfss_req_show(long nodeh, struct sysfs_ops *ops, void *instance)
{
	dkprintf("sysfss_req_show(%#lx,%p,%p)\n", nodeh, ops, instance);

	sysfss_req_show_logged_result(nodeh, ops, instance, sysfs_data_buf,
			sysfs_data_bufsize, (uintptr_t)ops->show,
			sysfss_show_bridge, sysfss_send_bridge,
			sysfss_req_show_log_bridge, NULL, NULL);
	return;
} /* sysfss_req_show() */

static void
sysfss_req_show_log_bridge(int event, long nodeh, void *ops, void *instance,
		size_t size, int error, int packet_err, ssize_t ssize)
{
	if (event == SYSFSS_REQ_LOG_CALLBACK_ERROR) {
		ekprintf("sysfss_req_show:->show failed. %ld\n", ssize);
	}
	else if (event == SYSFSS_REQ_LOG_SEND_ERROR) {
		ekprintf("sysfss_req_show:ihk_ikc_send failed. %d\n", error);
	}
	else if (event == SYSFSS_REQ_LOG_PACKET_ERROR) {
		ekprintf("sysfss_req_show(%#lx,%p,%p): %d %d\n",
				nodeh, ops, instance, error, packet_err);
	}
	else if (event == SYSFSS_REQ_LOG_DEBUG) {
		dkprintf("sysfss_req_show(%#lx,%p,%p): %d %d %ld\n",
			nodeh, ops, instance, error, packet_err, ssize);
	}
	(void)size;
}

static void
sysfss_req_store(long nodeh, struct sysfs_ops *ops, void *instance,
		size_t size)
{
	dkprintf("sysfss_req_store(%#lx,%p,%p,%d)\n",
			nodeh, ops, instance, size);

	sysfss_req_store_logged_result(nodeh, ops, instance, sysfs_data_buf,
			size, (uintptr_t)ops->store, sysfss_store_bridge,
			sysfss_send_bridge, sysfss_req_store_log_bridge,
			NULL, NULL);
	return;
} /* sysfss_req_store() */

static void
sysfss_req_store_log_bridge(int event, long nodeh, void *ops, void *instance,
		size_t size, int error, int packet_err, ssize_t ssize)
{
	if (event == SYSFSS_REQ_LOG_CALLBACK_ERROR) {
		ekprintf("sysfss_req_store:->store failed. %ld\n", ssize);
	}
	else if (event == SYSFSS_REQ_LOG_SEND_ERROR) {
		ekprintf("sysfss_req_store:ihk_ikc_send failed. %d\n", error);
	}
	else if (event == SYSFSS_REQ_LOG_PACKET_ERROR) {
		ekprintf("sysfss_req_store(%#lx,%p,%p,%d): %d %d\n",
				nodeh, ops, instance, size, error, packet_err);
	}
	else if (event == SYSFSS_REQ_LOG_DEBUG) {
		dkprintf("sysfss_req_store(%#lx,%p,%p,%d): %d %d %ld\n",
				nodeh, ops, instance, size, error, packet_err,
				ssize);
	}
}

static void
sysfss_req_release(long nodeh, struct sysfs_ops *ops, void *instance)
{
	dkprintf("sysfss_req_release(%#lx,%p,%p)\n", nodeh, ops, instance);

	sysfss_req_release_logged_result(nodeh, ops, instance,
			(uintptr_t)ops->release, sysfss_release_bridge,
			sysfss_send_bridge, sysfss_req_release_log_bridge,
			NULL);
	return;
} /* sysfss_req_release() */

static void
sysfss_req_release_log_bridge(int event, long nodeh, void *ops,
		void *instance, size_t size, int error, int packet_err,
		ssize_t ssize)
{
	if (event == SYSFSS_REQ_LOG_SEND_ERROR) {
		ekprintf("sysfss_req_release:ihk_ikc_send failed. %d\n",
				error);
	}
	else if (event == SYSFSS_REQ_LOG_PACKET_ERROR) {
		ekprintf("sysfss_req_release(%#lx,%p,%p): %d %d\n",
				nodeh, ops, instance, error, packet_err);
	}
	else if (event == SYSFSS_REQ_LOG_DEBUG) {
		dkprintf("sysfss_req_release(%#lx,%p,%p): %d %d\n",
				nodeh, ops, instance, error, packet_err);
	}
	(void)size;
	(void)ssize;
}

static void
sysfss_packet_show_bridge(long nodeh, void *ops, void *instance)
{
	sysfss_req_show(nodeh, ops, instance);
}

static void
sysfss_packet_store_bridge(long nodeh, void *ops, void *instance, size_t size)
{
	sysfss_req_store(nodeh, ops, instance, size);
}

static void
sysfss_packet_release_bridge(long nodeh, void *ops, void *instance)
{
	sysfss_req_release(nodeh, ops, instance);
}

static void
sysfss_packet_unknown_bridge(int msg, int error, long arg1, long arg2,
		long arg3)
{
	kprintf("sysfss_packet_handler:unknown message. msg %d"
			" error %d arg1 %#lx arg2 %#lx arg3 %#lx\n",
			msg, error, arg1, arg2, arg3);
}

void
sysfss_packet_handler(struct ihk_ikc_channel_desc *ch, int msg, int error,
		long arg1, long arg2, long arg3)
{
	sysfss_packet_handler_logged_result(msg, error, arg1, arg2, arg3,
			sysfss_packet_show_bridge, sysfss_packet_store_bridge,
			sysfss_packet_release_bridge,
			sysfss_packet_unknown_bridge, NULL);
	return;
} /* sysfss_packet_handler() */

void
sysfs_init(void)
{
	int error;
	int stage = SYSFS_INIT_STAGE_NONE;
	int phase = SYSFS_REQUEST_PHASE_NONE;

	dkprintf("sysfs_init()\n");

	error = sysfs_init_body_result(
			sizeof(struct sysfs_req_create_param),
			sizeof(struct sysfs_req_mkdir_param),
			sizeof(struct sysfs_req_symlink_param),
			sizeof(struct sysfs_req_lookup_param),
			sizeof(struct sysfs_req_unlink_param),
			sizeof(struct sysfs_req_setup_param),
			&sysfs_data_buf, &sysfs_data_bufsize,
			sysfs_init_alloc_bridge, sysfs_init_free_bridge,
			sysfs_init_phys_bridge, sysfs_request_send_bridge,
			sysfs_request_pause_bridge, sysfs_request_barrier_bridge,
			&stage, &phase);
	if (error) {
		if (stage == SYSFS_INIT_STAGE_SIZE) {
			ekprintf("sysfs_init:struct sysfs_*_req_param too large. %d\n",
					error);
			panic("struct sysfs_*_req_param too large");
		}
		else if (stage == SYSFS_INIT_STAGE_DATA_ALLOC) {
			ekprintf("sysfs_init:allocate_pages(buf) failed. %d\n",
					error);
		}
		else if (stage == SYSFS_INIT_STAGE_PARAM_ALLOC) {
			ekprintf("sysfs_init:allocate_pages(param) failed. %d\n",
					error);
		}
		else if (stage == SYSFS_INIT_STAGE_REQUEST &&
			 phase == SYSFS_REQUEST_PHASE_SEND) {
			ekprintf("sysfs_init:ihk_ikc_send failed. %d\n",
					error);
		}
		else if (stage == SYSFS_INIT_STAGE_REQUEST &&
			 phase == SYSFS_REQUEST_PHASE_RESPONSE) {
			ekprintf("sysfs_init:SCD_MSG_SYSFS_REQ_SETUP"
					" failed. %d\n", error);
		}
		ekprintf("sysfs_init(): %d\n", error);
		panic("sysfs_init");
	}
	dkprintf("sysfs_init():\n");
	return;
} /* sysfs_init() */

/**** End of File ****/
