/* Functional OS/apps and Rust migration only; no security testing.
 * Exact selected current C bodies, symbols renamed only, WITH_KRM off. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <sys/ioctl.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihk_rusage.h>
#ifdef WITH_KRM
#error Selected CPU successor requires WITH_KRM=OFF
#endif
#define dprintf(...) do {} while(0)
#define dnprintk(...) do {} while(0)
#define dprintk(...) do {} while(0)
static int ref_ihklib_device_readable(int index)
{
	int ret;
	char fn[PATH_MAX];

	sprintf(fn, "/dev/mcd%d", index);
	ret = access(fn, R_OK);
	if (ret) {
		ret = -errno;
		dnprintk(fn, "%s: error: access: path: %s, errno: %d\n",
			 __func__, _fn, -ret);
		goto out;
	}

	ret = 0;
 out:
	return ret;
}

int ref_ihklib_device_open(int index)
{
	int ret;
	char fn[PATH_MAX];

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		dprintf("%s: error: ref_ihklib_device_readable returned %d\n",
			__func__, ret);
		goto out;
	}

	sprintf(fn, "/dev/mcd%d", index);
	if ((ret = open(fn, O_RDONLY)) == -1) {
		ret = -errno;
		dnprintk(fn, "%s: error: open %s: %s\n",
			 __func__, _fn, strerror(-ret));
		goto out;
	}

 out:
	return ret;
}

int ref_ihk_reserve_cpu(int index, int* cpus, int num_cpus)
{
	int ret;
	struct ihk_cpu_req req = { 0 };
	int fd = -1;
#ifdef WITH_KRM
	int *nodeids = NULL;
	int nr_nodeids;
	int i;
#endif

	dprintk("%s: enter\n", __func__);

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (num_cpus < 0 || num_cpus > IHK_MAX_NUM_CPUS) {
		dprintf("%s: invalid number of cpus (%d)\n",
			__func__, num_cpus);
		ret = -EINVAL;
		goto out;
	}

	if (num_cpus != 0 && cpus == NULL) {
		ret = -EFAULT;
		goto out;
	}

	if (num_cpus == 0) {
		ret = 0;
		goto out;
	}

#ifdef WITH_KRM
	/* Included in cgroup cpuset.mems? We refer to cpuset.mems
	 * because cpuset.cpus includes both system cpus and job cpus
	 * but cpuset.mems only includes job NUMA-nodes.
	 */
	ret = parse_cpuset_mems(&nodeids, &nr_nodeids);
	if (ret) {
		dprintf("%s: error: parse_cpuset_mems failed with %d\n",
			__func__, ret);
		goto out;
	}

	for (i = 0; i < num_cpus; i++) {
		int found = 0;
		int j;

		char path[4096];
		DIR *dir = NULL;
		struct dirent *direp;
		int nodeid;

		sprintf(path, "/sys/devices/system/cpu/cpu%d/", cpus[i]);
		dir = opendir(path);
		if (dir == NULL) {
			if (errno == ENOENT) {
				dprintf("%s: error: cpu %d doesn't exist\n",
					__func__, cpus[i]);
				ret = -EINVAL;
				closedir(dir);
				goto out;
			}
			ret = -errno;
			dprintf("%s: error: opendir returned %d\n",
				__func__, -ret);
			closedir(dir);
			goto out;
		}

		while ((direp = readdir(dir))) {
			ret = sscanf(direp->d_name, "node%d", &nodeid);
			if (ret == 1) {
				break;
			}
		}
		closedir(dir);

		if (ret != 1) {
			dprintf("%s: error: numa to which cpu %d is attached not found\n",
				__func__, cpus[i]);
			ret = -EINVAL;
			goto out;
		}

		for (j = 0; j < nr_nodeids; j++) {
			if (nodeid == nodeids[j]) {
				found = 1;
				break;
			}
		}

		if (!found) {
			char *slice_cpuset_mems = NULL;

			(void)get_slice_cpuset_mems(&slice_cpuset_mems);
			dprintf("%s: error: numa %d associated with cpu %d is outside %s\n",
				__func__, nodeid, cpus[i],
				slice_cpuset_mems);
			free(slice_cpuset_mems);
			ret = -EINVAL;
			goto out;
		}
	}
#endif
	req.cpus = cpus;
	req.num_cpus = num_cpus;

	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: error: ref_ihklib_device_open returned %d\n",
			__func__, fd);
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_RESERVE_CPU, &req);
	if (ret) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_RESERVE_CPU returned %d\n",
			__func__, -ret);
		goto out;
	}

 out:
#ifdef WITH_KRM
	free(nodeids);
#endif
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_release_cpu(int index, int* cpus, int num_cpus)
{
	int ret;
	struct ihk_cpu_req req = { 0 };
	int fd = -1;

	dprintk("%s: enter\n", __func__);

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (num_cpus < 0 || num_cpus > IHK_MAX_NUM_CPUS) {
		dprintf("%s: invalid num_cpus: %d\n",
			__func__, num_cpus);
		ret = -EINVAL;
		goto out;
	}

	if (num_cpus != 0 && cpus == NULL) {
		ret = -EFAULT;
		goto out;
	}

	if (num_cpus == 0) {
		ret = 0;
		goto out;
	}

	req.cpus = cpus;
	req.num_cpus = num_cpus;

	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: error: ref_ihklib_device_open\n",
			__func__);
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_RELEASE_CPU, &req);
	if (ret) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_RELEASE_CPU returned %d\n",
			__func__, -ret);
		goto out;
	}
 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_get_num_reserved_cpus(int index)
{
	int ret;
	int fd = -1;

	dprintk("%s: enter\n", __func__);
	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: ref_ihklib_device_open returned %d\n",
			__func__, fd);
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_GET_NUM_CPUS);
	if (ret < 0) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_GET_NUM_CPUS returned %d\n",
			__func__, -ret);
		goto out;
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_query_cpu(int index, int *cpus, int num_cpus)
{
	int ret;
	struct ihk_cpu_req req = { 0 };
	int fd = -1;

	dprintk("%s: enter\n", __func__);

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (cpus == NULL || num_cpus < 0 || num_cpus > IHK_MAX_NUM_CPUS) {
		dprintf("%s: invalid number of cpus (%d)\n",
			__func__, num_cpus);
		ret = -EINVAL;
		goto out;
	}

	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: ref_ihklib_device_open returned %d\n",
			__func__, fd);
		ret = fd;
		goto out;
	}

	if ((ret = ioctl(fd, IHK_DEVICE_GET_NUM_CPUS)) < 0) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_GET_NUM_CPUS returned %d\n",
			__func__, -ret);
		goto out;
	}

	if (ret != num_cpus) {
		dprintf("%s: error: actual # of cpus (%d) != requested (%d)\n",
			__func__, ret, num_cpus);
		ret = -EINVAL;
		goto out;
	}

	/* num_cpus of zero is a valid input */
	if (num_cpus == 0) {
		ret = 0;
		goto out;
	}

	req.cpus = cpus;
	req.num_cpus = num_cpus;

	if ((ret = ioctl(fd, IHK_DEVICE_QUERY_CPU, &req))) {
		ret = -errno;
		dprintf("%s: error: IHK_DEVICE_QUERY_CPU returned %d\n",
			__func__, -ret);
		goto out;
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}
