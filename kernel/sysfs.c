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

	packet.msg = msg;
	packet.err = err;
	packet.sysfs_arg1 = arg1;
	packet.sysfs_arg2 = arg2;
	return ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
}

static int setup_special_create(struct sysfs_req_create_param *param, struct sysfs_bitmap_param *pbp)
{
	void *cinstance = (void *)param->client_instance;

	switch (sysfs_special_kind_result(param->client_ops)) {
	case SYSFS_SPECIAL_KIND_DIRECT:
		param->client_instance = virt_to_phys(cinstance);
		return 0;

	case SYSFS_SPECIAL_KIND_STRING:
		pbp->nbits = sysfs_string_nbits_result(strlen(cinstance));
		pbp->ptr = (void *)virt_to_phys(cinstance);
		param->client_instance = virt_to_phys(pbp);
		return 0;

	case SYSFS_SPECIAL_KIND_BITMAP:
		*pbp = *(struct sysfs_bitmap_param *)cinstance;
		pbp->ptr = (void *)virt_to_phys(pbp->ptr);
		param->client_instance = virt_to_phys(pbp);
		return 0;
	}

	ekprintf("setup_special_create:unknown ops %#lx\n", param->client_ops);
	return -EINVAL;
} /* setup_special_create() */

int
sysfs_createf(struct sysfs_ops *ops, void *instance, int mode,
		const char *fmt, ...)
{
	int error;
	va_list ap;
	ssize_t n;
	struct sysfs_req_create_param *param = NULL;
	struct ikc_scd_packet packet;
	struct sysfs_bitmap_param asbp;

	dkprintf("sysfs_createf(%p,%p,%#o,%s,...)\n",
			ops, instance, mode, fmt);

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
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

	packet.msg = SCD_MSG_SYSFS_REQ_CREATE;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_createf:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_createf:SCD_MSG_SYSFS_REQ_CREATE failed. %d\n",
				error);
		goto out;
	}

	error = 0;
out:
	if (param) {
		ihk_mc_free_pages(param, 1);
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
	struct ikc_scd_packet packet;
	va_list ap;
	int n;

	dkprintf("sysfs_mkdirf(%p,%s,...)\n", dirhp, fmt);

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
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

	packet.msg = SCD_MSG_SYSFS_REQ_MKDIR;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_mkdirf:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_mkdirf:SCD_MSG_SYSFS_REQ_MKDIR failed. %d\n",
				error);
		goto out;
	}

	error = 0;
	if (sysfs_handle_pointer_valid_result((uintptr_t)dirhp)) {
		dirhp->handle = param->handle;
	}

out:
	if (param) {
		ihk_mc_free_pages(param, 1);
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
	struct ikc_scd_packet packet;
	va_list ap;
	int n;

	dkprintf("sysfs_symlinkf(%#lx,%s,...)\n", targeth.handle, fmt);

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
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

	packet.msg = SCD_MSG_SYSFS_REQ_SYMLINK;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_symlinkf:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_symlinkf:"
				"SCD_MSG_SYSFS_REQ_SYMLINK failed. %d\n",
				error);
		goto out;
	}

	error = 0;
out:
	if (param) {
		ihk_mc_free_pages(param, 1);
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
	struct ikc_scd_packet packet;
	va_list ap;
	int n;

	dkprintf("sysfs_lookupf(%p,%s,...)\n", objhp, fmt);

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
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

	packet.msg = SCD_MSG_SYSFS_REQ_LOOKUP;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_lookupf:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_lookupf:SCD_MSG_SYSFS_REQ_LOOKUP failed. %d\n",
				error);
		goto out;
	}

	error = 0;
	if (sysfs_handle_pointer_valid_result((uintptr_t)objhp)) {
		objhp->handle = param->handle;
	}

out:
	if (param) {
		ihk_mc_free_pages(param, 1);
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
	struct ikc_scd_packet packet;
	va_list ap;
	int n;

	dkprintf("sysfs_unlinkf(%#x,%s,...)\n", flags, fmt);

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
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

	packet.msg = SCD_MSG_SYSFS_REQ_UNLINK;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_unlinkf:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_unlinkf:SCD_MSG_SYSFS_REQ_UNLINK failed. %d\n",
				error);
		goto out;
	}

	error = 0;
out:
	if (param) {
		ihk_mc_free_pages(param, 1);
	}
	if (error) {
		ekprintf("sysfs_unlinkf(%#x,%s,...): %d\n", flags, fmt, error);
	}
	dkprintf("sysfs_unlinkf(%#x,%s,...): %d\n", flags, fmt, error);
	return error;
} /* sysfs_unlinkf() */

static void
sysfss_req_show(long nodeh, struct sysfs_ops *ops, void *instance)
{
	int error;
	int packet_err;
	ssize_t ssize;
	sysfss_show_fn_t show_fn = NULL;

	dkprintf("sysfss_req_show(%#lx,%p,%p)\n", nodeh, ops, instance);

	if (sysfs_should_call_show_result((uintptr_t)ops->show)) {
		show_fn = sysfss_show_bridge;
	}

	error = sysfss_req_show_body_result(nodeh, ops, instance,
			sysfs_data_buf, sysfs_data_bufsize, show_fn,
			sysfss_send_bridge, &ssize, &packet_err);

	if (show_fn && ssize < 0) {
		ekprintf("sysfss_req_show:->show failed. %ld\n", ssize);
		/* through */
	}
	if (error) {
		ekprintf("sysfss_req_show:ihk_ikc_send failed. %d\n", error);
		/* through */
	}

	if (sysfs_packet_error_result(error, packet_err)) {
		ekprintf("sysfss_req_show(%#lx,%p,%p): %d %d\n",
				nodeh, ops, instance, error, packet_err);
	}
	dkprintf("sysfss_req_show(%#lx,%p,%p): %d %d %ld\n",
			nodeh, ops, instance, error, packet_err, ssize);
	return;
} /* sysfss_req_show() */

static void
sysfss_req_store(long nodeh, struct sysfs_ops *ops, void *instance,
		size_t size)
{
	int error;
	int packet_err;
	ssize_t ssize;
	sysfss_store_fn_t store_fn = NULL;

	dkprintf("sysfss_req_store(%#lx,%p,%p,%d)\n",
			nodeh, ops, instance, size);

	if (sysfs_should_call_store_result((uintptr_t)ops->store)) {
		store_fn = sysfss_store_bridge;
	}

	error = sysfss_req_store_body_result(nodeh, ops, instance,
			sysfs_data_buf, size, store_fn, sysfss_send_bridge,
			&ssize, &packet_err);

	if (store_fn && ssize < 0) {
		ekprintf("sysfss_req_store:->store failed. %ld\n", ssize);
		/* through */
	}
	if (error) {
		ekprintf("sysfss_req_store:ihk_ikc_send failed. %d\n", error);
		/* through */
	}

	if (sysfs_packet_error_result(error, packet_err)) {
		ekprintf("sysfss_req_store(%#lx,%p,%p,%d): %d %d\n",
				nodeh, ops, instance, size, error, packet_err);
	}
	dkprintf("sysfss_req_store(%#lx,%p,%p,%d): %d %d %ld\n",
			nodeh, ops, instance, size, error, packet_err, ssize);
	return;
} /* sysfss_req_store() */

static void
sysfss_req_release(long nodeh, struct sysfs_ops *ops, void *instance)
{
	int error;
	int packet_err;
	sysfss_release_fn_t release_fn = NULL;

	dkprintf("sysfss_req_release(%#lx,%p,%p)\n", nodeh, ops, instance);

	if (sysfs_should_call_release_result((uintptr_t)ops->release)) {
		release_fn = sysfss_release_bridge;
	}

	error = sysfss_req_release_body_result(nodeh, ops, instance,
			release_fn, sysfss_send_bridge, &packet_err);
	if (error) {
		ekprintf("sysfss_req_release:ihk_ikc_send failed. %d\n",
				error);
		/* through */
	}

	if (sysfs_packet_error_result(error, packet_err)) {
		ekprintf("sysfss_req_release(%#lx,%p,%p): %d %d\n",
				nodeh, ops, instance, error, packet_err);
	}
	dkprintf("sysfss_req_release(%#lx,%p,%p): %d %d\n",
			nodeh, ops, instance, error, packet_err);
	return;
} /* sysfss_req_release() */

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

void
sysfss_packet_handler(struct ihk_ikc_channel_desc *ch, int msg, int error,
		long arg1, long arg2, long arg3)
{
	int kind;

	sysfss_packet_handler_body_result(msg, error, arg1, arg2, arg3,
			sysfss_packet_show_bridge, sysfss_packet_store_bridge,
			sysfss_packet_release_bridge, &kind);

	if (kind == SYSFS_HANDLER_UNKNOWN) {
		kprintf("sysfss_packet_handler:unknown message. msg %d"
				" error %d arg1 %#lx arg2 %#lx arg3 %#lx\n",
				msg, error, arg1, arg2, arg3);
	}
	return;
} /* sysfss_packet_handler() */

void
sysfs_init(void)
{
	int error;
	struct sysfs_req_setup_param *param = NULL;
	struct ikc_scd_packet packet;

	dkprintf("sysfs_init()\n");

	if (!sysfs_param_sizes_valid_result(
			sizeof(struct sysfs_req_create_param),
			sizeof(struct sysfs_req_mkdir_param),
			sizeof(struct sysfs_req_symlink_param),
			sizeof(struct sysfs_req_lookup_param),
			sizeof(struct sysfs_req_unlink_param),
			sizeof(struct sysfs_req_setup_param))) {
		panic("struct sysfs_*_req_param too large");
	}

	sysfs_data_bufsize = sysfs_data_bufsize_result();
	sysfs_data_buf = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
	if (sysfs_pointer_missing_result((uintptr_t)sysfs_data_buf)) {
		error = -ENOMEM;
		ekprintf("sysfs_init:allocate_pages(buf) failed. %d\n", error);
		goto out;
	}

	param = ihk_mc_alloc_pages(1, IHK_MC_AP_NOWAIT);
	if (sysfs_pointer_missing_result((uintptr_t)param)) {
		error = -ENOMEM;
		ekprintf("sysfs_init:allocate_pages(param) failed. %d\n",
				error);
		goto out;
	}

	param->busy = 1;
	param->buf_rpa = virt_to_phys(sysfs_data_buf);
	param->bufsize = sysfs_data_bufsize_result();

	packet.msg = SCD_MSG_SYSFS_REQ_SETUP;
	packet.sysfs_arg1 = virt_to_phys(param);

	error = ihk_ikc_send(cpu_local_var(ikc2linux), &packet, 0);
	if (error) {
		ekprintf("sysfs_init:ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (sysfs_request_busy_result(param->busy)) {
		cpu_pause();
	}
	rmb();

	error = param->error;
	if (error) {
		ekprintf("sysfs_init:SCD_MSG_SYSFS_REQ_SETUP failed. %d\n",
				error);
		goto out;
	}

	error = 0;
out:
	if (param) {
		ihk_mc_free_pages(param, 1);
	}
	if (error) {
		ekprintf("sysfs_init(): %d\n", error);
		panic("sysfs_init");
	}
	dkprintf("sysfs_init():\n");
	return;
} /* sysfs_init() */

/**** End of File ****/
