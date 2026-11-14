/* Functional OS/apps and Rust migration only; no security testing.
 * Original selected ENABLE_RUSAGE=1 bodies; reference-only symbol renaming. */
#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihk_rusage.h>
#include <ihk/ihklib.h>
#define dprintf(...) do {} while(0)
#define dprintk(...) do {} while(0)
#define dnprintk(...) do {} while(0)
struct mcctrl_ioctl_getrusage_desc {struct ihk_os_rusage *rusage;size_t size_rusage;};
static int ref_ihklib_os_readable(int index)
{
	int ret;
	char fn[PATH_MAX];

	sprintf(fn, "/dev/mcos%d", index);
	ret = access(fn, R_OK);
	if (ret) {
		ret = -errno;
		dnprintk(fn, "%s: error: access: path: %s, errno: %d\n",
			 "ihklib_os_readable", _fn, -ret);
		goto out;
	}

 out:
	return ret;
}

int ref_ihklib_os_open(int index)
{
	int ret;
	char fn[PATH_MAX];

	ret = ref_ihklib_os_readable(index);
	if (ret) {
		dprintf("%s: error: ihklib_os_readable returned %d\n",
			"ihklib_os_open", ret);
		goto out;
	}

	sprintf(fn, "/dev/mcos%d", index);

	if ((ret = open(fn, O_RDONLY)) == -1) {
		ret = -errno;
		dnprintk(fn, "%s: error: open %s: %s\n",
			 "ihklib_os_open", _fn, strerror(-ret));
		goto out;
	}

 out:
	return ret;
}

int ref_ihk_os_get_num_numa_nodes(int index)
{
	int ret;
	int fd = -1;

	dprintk("%s: enter\n", "ihk_os_get_num_numa_nodes");

	if ((fd = ref_ihklib_os_open(index)) < 0) {
		dprintf("%s: error: ihklib_os_open\n",
			"ihk_os_get_num_numa_nodes");
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_OS_GET_NUM_NUMA_NODES);
	if (ret < 0) {
		ret = -errno;
		dprintf("%s: IHK_OS_GET_NUM_NUMA_NODES returned %d\n",
			"ihk_os_get_num_numa_nodes", -ret);
		goto out;
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_os_getrusage(int index, struct ihk_os_rusage *rusage,
		     size_t size_rusage)
{
	int ret;
	int fd = -1;

	dprintk("%s: enter\n", "ihk_os_getrusage");

	if (!rusage) {
		dprintf("%s: error: output buffer is NULL\n",
			"ihk_os_getrusage");
		ret = -EFAULT;
		goto out;
	}

	if (size_rusage != sizeof(struct ihk_os_rusage)) {
		dprintf("%s: error: size of output buffer is invalid\n",
			"ihk_os_getrusage");
		ret = -EINVAL;
		goto out;
	}

	struct mcctrl_ioctl_getrusage_desc desc = {
		.rusage = rusage,
		.size_rusage = size_rusage,
	};

	if ((fd = ref_ihklib_os_open(index)) < 0) {
		dprintf("%s: error: ihklib_os_open returned %d\n",
			"ihk_os_getrusage", fd);
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_OS_GETRUSAGE, &desc);
	if (ret) {
		ret = -errno;
		dprintf("%s: IHK_OS_GETRUSAGE returned %d\n",
			"ihk_os_getrusage", -ret);
		goto out;
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	dprintk("%s: returning %d\n", "ihk_os_getrusage", ret);
	return ret;
}
