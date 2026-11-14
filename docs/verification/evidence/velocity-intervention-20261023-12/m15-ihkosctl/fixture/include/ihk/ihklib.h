#pragma once
#include <sys/types.h>
#include <ihk/ihk_host_user.h>
enum ihklib_os_status {
	IHK_STATUS_INACTIVE,
	IHK_STATUS_BOOTING,
	IHK_STATUS_RUNNING,
	IHK_STATUS_SHUTDOWN, /* shutting-down */
	IHK_STATUS_PANIC,
	IHK_STATUS_HUNGUP,
	IHK_STATUS_FREEZING,
	IHK_STATUS_FROZEN,
};
int ihk_os_get_status(int index);
int ihk_os_kmsg(int index, char* kmsg, ssize_t sz_kmsg);
int ihk_os_makedumpfile(int index, char *dump_file, int dump_level, int interactive);
