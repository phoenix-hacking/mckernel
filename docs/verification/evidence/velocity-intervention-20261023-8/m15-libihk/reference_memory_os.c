/* Functional OS/apps and Rust migration only; no security testing.
 * Original current C bodies, public symbols/global state renamed only. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <dirent.h>
#include <sys/ioctl.h>
#include "selected_memory_layout.h"
#define IHK_MAX_NUM_MEM_CHUNKS 2048
#define IHK_SMP_MEM_ALL (-1UL)
#define IHKLIB_LINUX_KMSG_SIZE (4096-256)
#ifdef WITH_KRM
#error KRM profile not ported or selected
#endif
#define dprintf(...) do {} while(0)
#define dnprintk(...) do {} while(0)
#define dprintk(...) do {} while(0)
#define CHKANDJUMP(cond,err,...) do { if(cond) {ret=err;goto out;} } while(0)
extern int loglevel;
int ref_ihklib_device_open(int);
int ref_ihk_get_num_reserved_mem_chunks(int);
int ref_ihk_query_mem(int,struct ihk_mem_chunk*,int);
int ref_ihk_release_mem(int,struct ihk_mem_chunk*,int);
struct ihklib_reserve_mem_conf ref_reserve_mem_conf={0,0,0,4096,98,30};
static const struct ihklib_reserve_mem_conf ref_reserve_mem_conf_default={0,0,0,4096,98,30};
#define printk(fmt, args...) do {					\
	char contents[IHKLIB_LINUX_KMSG_SIZE];				\
	int _fd;							\
	ssize_t len;							\
	ssize_t offset = 0;						\
	ssize_t written;						\
									\
	if (geteuid()) {						\
		break;							\
	}								\
	snprintf(contents, IHKLIB_LINUX_KMSG_SIZE, fmt, ##args);	\
	_fd = open("/dev/kmsg", O_WRONLY);				\
	len = strnlen(contents, IHKLIB_LINUX_KMSG_SIZE - 1) + 1;	\
	while (offset < len) {						\
		written = write(_fd, contents + offset, len - offset);	\
		if (written <= 0) {					\
			break;						\
		}							\
		offset += written;					\
	}								\
	close(_fd);							\
} while (0)
#define eprintf(fmt,args...) do { if(loglevel>=1) {printk(fmt,##args);} } while(0)
static int ref_ihklib_device_readable(int index)
{
	int ret;
	char fn[PATH_MAX];

	sprintf(fn, "/dev/mcd%d", index);
	ret = access(fn, R_OK);
	if (ret) {
		ret = -errno;
		dnprintk(fn, "%s: error: access: path: %s, errno: %d\n",
			 "ihklib_device_readable", _fn, -ret);
		goto out;
	}

	ret = 0;
 out:
	return ret;
}

int ref_ihk_reserve_mem(int index, struct ihk_mem_chunk *mem_chunks,
		    int num_mem_chunks)
{
	int ret;
	int i;
	struct ihk_mem_req req = { 0 };
	int fd = -1;

	size_t total_requested = 0, total_avail = 0;
	int num_mem_chunks_reserved;
	struct ihk_mem_chunk *mem_chunks_reserved = NULL;
	size_t *reserved = NULL;
	int num_numa_nodes = 0;
	int num_numa_nodes_compensate = 0;
	int num_numa_nodes_release = 0;
	size_t ave_requested;
	size_t total_missing = 0, total_excess = 0;
	size_t ave_compensate;
	size_t total_missing2 = 0, total_excess2 = 0;
	size_t ave_compensate2;
	unsigned long min = (unsigned long)-1;
	unsigned long max = 0;
	unsigned long variance_limit;
	int release = 0;
#ifdef WITH_KRM
	int *nodeids = NULL;
	int nr_nodeids;
#endif

	dprintk("%s: reserve_mem_conf.balanced_enable=%d\n",
		"ihk_reserve_mem", ref_reserve_mem_conf.balanced_enable);

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (num_mem_chunks < 0 || num_mem_chunks > IHK_MAX_NUM_MEM_CHUNKS) {
		dprintf("%s: error: invalid # of chunks (%d)\n",
			"ihk_reserve_mem", num_mem_chunks);
		ret = -EINVAL;
		goto out;
	}

	if (num_mem_chunks != 0 && mem_chunks == NULL) {
		ret = -EFAULT;
		goto out;
	}

	if (num_mem_chunks == 0) {
		ret = 0;
		goto out;
	}

#ifdef WITH_KRM
	/* Included in cgroup cpuset.mems? */
	ret = parse_cpuset_mems(&nodeids, &nr_nodeids);
	if (ret) {
		dprintf("%s: error: parse_cpuset_mems failed with %d\n",
			"ihk_reserve_mem", ret);
		goto out;
	}

	for (i = 0; i < num_mem_chunks; i++) {
		int found = 0;
		int j;

		for (j = 0; j < nr_nodeids; j++) {
			if (mem_chunks[i].numa_node_number == nodeids[j]) {
				found = 1;
				break;
			}
		}

		if (!found) {
			char *slice_cpuset_mems = NULL;

			(void)get_slice_cpuset_mems(&slice_cpuset_mems);
			dprintf("%s: error: numa %d is outside %s\n",
				"ihk_reserve_mem",
				mem_chunks[i].numa_node_number,
				slice_cpuset_mems);
			free(slice_cpuset_mems);
			ret = -EINVAL;
			goto out;
		}
	}
#endif

	req.sizes = calloc(num_mem_chunks, sizeof(size_t));
	if (!req.sizes) {
		dprintf("%s: error: allocating req.sizes\n",
			"ihk_reserve_mem");
		ret = -ENOMEM;
		goto out;
	}

	req.numa_ids = calloc(num_mem_chunks, sizeof(int));
	if (!req.numa_ids) {
		dprintf("%s: error: allocating req.numa_ids\n",
			"ihk_reserve_mem");
		ret = -ENOMEM;
		goto out;
	}

	for (i = 0; i < num_mem_chunks; i++) {
		if (ref_reserve_mem_conf.balanced_enable) {
			req.sizes[i] = (size_t)IHK_SMP_MEM_ALL;
			total_requested += (size_t)mem_chunks[i].size;
		} else {
			req.sizes[i] = (size_t)mem_chunks[i].size;
		}
		req.numa_ids[i] = mem_chunks[i].numa_node_number;
	}
	req.num_chunks = num_mem_chunks;
	req.min_chunk_size = ref_reserve_mem_conf.min_chunk_size;
	req.max_size_ratio_all = ref_reserve_mem_conf.max_size_ratio_all;
	req.timeout = ref_reserve_mem_conf.timeout;

	fd = ref_ihklib_device_open(index);
	if (fd < 0) {
		ret = fd;
		printf("%s: ihklib_device_open returned %d\n",
		       "ihk_reserve_mem", fd);
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_RESERVE_MEM, &req);
	if (ret != 0) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_RESERVE_MEM returned %d\n",
			"ihk_reserve_mem", -ret);
		goto out;
	}

	close(fd);
	fd = -1;

	if (ref_reserve_mem_conf.balanced_enable) {
		/* for error-case detected by CHKANDJUMP */
		release = 1;

		dprintk("%s: total requested: %ld\n",
			"ihk_reserve_mem", total_requested);

		num_mem_chunks_reserved =
			ref_ihk_get_num_reserved_mem_chunks(index);
		mem_chunks_reserved = calloc(num_mem_chunks_reserved,
					  sizeof(struct ihk_mem_chunk));
		CHKANDJUMP(mem_chunks_reserved == NULL, -ENOMEM,
			   "failed to allocate mem_chunks_reserved\n");

		ret = ref_ihk_query_mem(index, mem_chunks_reserved,
				    num_mem_chunks_reserved);
		CHKANDJUMP(ret, -EINVAL, "ihk_query_mem failed\n");

		reserved = calloc(IHK_MAX_NUM_NUMA_NODES, sizeof(size_t));
		CHKANDJUMP(reserved == NULL, -ENOMEM,
			   "failed to allocate reserved\n");

		for (i = 0; i < num_mem_chunks_reserved; i++) {
			reserved[mem_chunks_reserved[i].numa_node_number] +=
				mem_chunks_reserved[i].size;
		}

		for (i = 0; i < IHK_MAX_NUM_NUMA_NODES; i++) {
			if (reserved[i] == 0) {
				continue;
			}
			num_numa_nodes++;
		}

/* align reserve/release amount */
#define IHKLIB_RESERVE_AMOUNT_ALIGN (1UL << 20)

		for (i = 0; i < IHK_MAX_NUM_NUMA_NODES; i++) {
			total_avail += reserved[i];
		}

		/* best-effort: reserve memory of up to requested amount */
		if (total_avail < total_requested) {
			dprintk("%s: info: best_effort: %d, "
				"available (%ld, %ld MiB) < "
				"requested (%ld, %ld MiB)\n",
				"ihk_reserve_mem",
				ref_reserve_mem_conf.balanced_best_effort,
				total_avail, total_avail >> 20,
				total_requested, total_requested >> 20);
			if (ref_reserve_mem_conf.balanced_best_effort) {
				total_requested = total_avail;
			} else {
				release = 1;
				ret = -ENOMEM;
				goto out;
			}
		}

		/* prevent following round-up from making requested
		 * exceed the cap
		 */
		if (ref_reserve_mem_conf.balanced_best_effort) {
			total_requested /=
				num_numa_nodes * IHKLIB_RESERVE_AMOUNT_ALIGN;
			total_requested *=
				num_numa_nodes * IHKLIB_RESERVE_AMOUNT_ALIGN;
			dprintk("%s: info: requsted trimmed to %ld, %ld MiB\n",
				"ihk_reserve_mem",
				total_requested, total_requested >> 20);
		}

		/* round up not to release too much */
		ave_requested = ((total_requested / num_numa_nodes +
				  IHKLIB_RESERVE_AMOUNT_ALIGN - 1) /
				 IHKLIB_RESERVE_AMOUNT_ALIGN) *
			IHKLIB_RESERVE_AMOUNT_ALIGN;
		dprintk("%s: ave requested: %ld\n",
			"ihk_reserve_mem", ave_requested);

		/* Fill below-average-of-requested nodes upto the average */
		for (i = 0; i < IHK_MAX_NUM_NUMA_NODES; i++) {
			if (reserved[i] == 0) {
				continue;
			}
			dprintk("%s: node id: %d, reserved: %ld\n",
				"ihk_reserve_mem", i, reserved[i]);
			if (reserved[i] > ave_requested) {
				num_numa_nodes_compensate++;
				total_excess += reserved[i] - ave_requested;
			} else {
				total_missing += ave_requested - reserved[i];
			}
		}

		if (total_missing > total_excess) {
			dprintf("%s: error: "
				"sum of below-ave (%ld, %ld MiB) > "
				"sum of above-ave (%ld, %ld MiB)\n",
				"ihk_reserve_mem",
				total_missing, total_missing >> 20,
				total_excess, total_excess >> 20);
			ret = -ENOMEM;
			goto out;
		}

		dprintk("%s: total missing: %ld, %ld MiB, "
			"total excess: %ld, %ld MiB\n",
			"ihk_reserve_mem",
			total_missing, total_missing >> 20,
			total_excess, total_excess >> 20
			);

		req.sizes = calloc(IHK_MAX_NUM_NUMA_NODES, sizeof(size_t));
		CHKANDJUMP(req.sizes == NULL, -ENOMEM,
			   "failed to allocate torelease\n");

		req.numa_ids = calloc(IHK_MAX_NUM_NUMA_NODES, sizeof(int));
		CHKANDJUMP(req.numa_ids == NULL, -ENOMEM,
			   "failed to allocate torelease\n");

		/* round up not to release too much */
		ave_compensate = ((total_missing / num_numa_nodes_compensate +
				   IHKLIB_RESERVE_AMOUNT_ALIGN - 1) /
				  IHKLIB_RESERVE_AMOUNT_ALIGN) *
			IHKLIB_RESERVE_AMOUNT_ALIGN;
		dprintk("%s: ave compensate: %ld\n",
			"ihk_reserve_mem", ave_compensate);

		/* Fill below ave(requested + compensation),
		 * compensating nodes upto the average
		 */
		for (i = 0; i < IHK_MAX_NUM_NUMA_NODES; i++) {
			if (reserved[i] <= ave_requested) {
				continue;
			}

			if (reserved[i] > ave_requested + ave_compensate) {
				num_numa_nodes_release++;
				total_excess2 += reserved[i] - ave_requested -
					ave_compensate;
				dprintk("%s: above-ave-req+comp: node id: %d, reserved: %ld, ave requested: %ld, ave compensate: %ld, compensate2+=%ld\n",
					"ihk_reserve_mem", i, reserved[i],
					ave_requested, ave_compensate,
					reserved[i] - ave_requested -
					ave_compensate);
			} else {
				total_missing2 += ave_requested +
					ave_compensate - reserved[i];
				dprintk("%s: below-ave-req+comp: node id: %d, reserved: %ld, ave requested: %ld, ave compensate: %ld, missing2+=%ld\n",
					"ihk_reserve_mem", i, reserved[i],
					ave_requested, ave_compensate,
					ave_requested + ave_compensate -
					reserved[i]);
			}
		}

		dprintk("%s: total excess2: %ld, total missing2: %ld\n",
			"ihk_reserve_mem", total_excess2, total_missing2);

		/* round up not to release too much */
		ave_compensate2 =
			((total_missing2 / num_numa_nodes_release +
			  IHKLIB_RESERVE_AMOUNT_ALIGN - 1) /
			 IHKLIB_RESERVE_AMOUNT_ALIGN) *
			IHKLIB_RESERVE_AMOUNT_ALIGN;
		dprintk("%s: ave compensate2: %ld\n",
			"ihk_reserve_mem", ave_compensate2);

		/* above-average-of-requested-plus-compensation nodes
		 * can release the excess amount
		 */
		for (i = 0; i < IHK_MAX_NUM_NUMA_NODES; i++) {
			req.numa_ids[i] = i;

			if (reserved[i] > ave_requested +
			    ave_compensate + ave_compensate2) {
				req.sizes[i] = reserved[i] - ave_requested -
					ave_compensate - ave_compensate2;
				if (reserved[i] < ave_requested +
					ave_compensate + ave_compensate2) {
					dprintk("%s: negative release size %ld\n",
						"ihk_reserve_mem", req.sizes[i]);
					ret = -EINVAL;
					goto out;
				}
			} else {
				req.sizes[i] = 0;
			}

			if (req.sizes[i] != 0) {
				dprintk("%s: node id: %d, to-release: %ld\n",
					"ihk_reserve_mem", i, req.sizes[i]);
			}

			if (reserved[i] > 0 &&
			    reserved[i] - req.sizes[i] < min) {
				min = reserved[i] - req.sizes[i];
			}
			if (reserved[i] > 0 &&
			    reserved[i] - req.sizes[i] > max) {
				max = reserved[i] - req.sizes[i];
			}
		}

		variance_limit = ave_requested *
			ref_reserve_mem_conf.balanced_variance_limit / 100;
		dprintk("%s: min: %ld, max: %ld, variance_limit: %ld\n",
			"ihk_reserve_mem", min, max, variance_limit);
		if (max - ave_requested > variance_limit ||
		    ave_requested - min > variance_limit) {
#ifdef DEBUG
			unsigned long max_ave = max - ave_requested;
			unsigned long ave_min = ave_requested - min;
#endif

			dprintf("%s: error: variance > limit, "
				"ave: %ld (%ld MiB), "
				"max - ave: %ld (%ld MiB), "
				"ave - min: %ld (%ld MiB), "
				"limit: %ld (%ld MiB)\n",
				"ihk_reserve_mem",
				ave_requested, ave_requested >> 20,
				max_ave, max_ave >> 20,
				ave_min, ave_min >> 20,
				variance_limit, variance_limit >> 20);

			release = 1;
			ret = -ENOMEM;
			goto out;
		}

		req.num_chunks = IHK_MAX_NUM_NUMA_NODES;

		fd = ref_ihklib_device_open(index);
		if (fd < 0) {
			ret = fd;
			dprintf("%s: ihklib_device_open returned %d\n",
				"ihk_reserve_mem", fd);
			goto out;
		}

		ret = ioctl(fd, IHK_DEVICE_RELEASE_MEM_PARTIALLY, &req);
		if (ret != 0) {
			ret = -errno;
			dprintf("%s: IHK_DEVICE_RELEASE_MEM_PARTIALLY returned %d\n",
				"ihk_reserve_mem", -ret);
			goto out;
		}

		close(fd);
		fd = -1;
		release = 0;
	}

	ret = 0;
out:

	/* ihk_reserve_mem_conf is one-shot */
	ref_reserve_mem_conf = ref_reserve_mem_conf_default;

#ifdef WITH_KRM
	free(nodeids);
#endif
	if (release) {
		struct ihk_mem_chunk mem_chunks[1] = {
			{ .size = -1UL, .numa_node_number = 0 }
		};

		ref_ihk_release_mem(index, mem_chunks, 1);
	}

	if (fd >= 0) {
		close(fd);
	}
	free(req.sizes);
	free(req.numa_ids);
	if (ref_reserve_mem_conf.balanced_enable) {
		free(mem_chunks_reserved);
		free(reserved);
	}
	return ret;
}

int ref_ihk_get_num_reserved_mem_chunks(int index)
{
	int ret;
	int fd = -1;
	struct ihk_mem_req req = { 0 };

	dprintk("%s: enter\n", "ihk_get_num_reserved_mem_chunks");
	if ((fd = ref_ihklib_device_open(index)) < 0) {
		eprintf("%s: ihklib_device_open failed with %d\n",
			"ihk_get_num_reserved_mem_chunks", fd);
		ret = fd;
		goto out;
	}

	req.num_chunks = 0;   /* means only get num_reserved_mem_chunks */

	ret = ioctl(fd, IHK_DEVICE_QUERY_MEM, &req);
	if (ret) {
		ret = -errno;
		dprintf("%s: IHK_DEVICE_QUERY_MEM returned %d\n",
			"ihk_get_num_reserved_mem_chunks", -ret);
		goto out;
	}

	ret = req.num_chunks;

 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_query_mem(int index, struct ihk_mem_chunk* mem_chunks, int _num_mem_chunks)
{
	int ret;
	int fd = -1;
	int i;
	int num_mem_chunks;
	struct ihk_mem_req req = { 0 };

	dprintk("%s: enter\n", "ihk_query_mem");
	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (_num_mem_chunks < 0 || _num_mem_chunks > IHK_MAX_NUM_MEM_CHUNKS) {
		dprintf("%s: error: invalid # of chunks (%d)\n",
			"ihk_query_mem", _num_mem_chunks);
		ret = -EINVAL;
		goto out;
	}

	if (_num_mem_chunks != 0 && mem_chunks == NULL) {
		ret = -EFAULT;
		goto out;
	}

	ret = ref_ihk_get_num_reserved_mem_chunks(index);
	if (ret < 0) {
		dprintf("%s: error: ihk_get_num_reserved_mem_chunks"
			" returned %d\n",
			"ihk_query_mem", ret);
		goto out;
	}
	num_mem_chunks = ret;

	if (_num_mem_chunks != num_mem_chunks) {
		dprintf("%s: error: actual # of chunks (%d) !="
			" requested (%d)\n",
			"ihk_query_mem", num_mem_chunks, _num_mem_chunks);
		ret = -EINVAL;
		goto out;
	}

	/* _num_mem_chunks of zero is a valid input */
	if (num_mem_chunks == 0) {
		ret = 0;
		goto out;
	}

	req.sizes = calloc(num_mem_chunks, sizeof(size_t));
	if (!req.sizes) {
		dprintf("%s: error: allocating request sizes\n",
			"ihk_query_mem");
		ret = -ENOMEM;
		goto out;
	}

	req.numa_ids = calloc(num_mem_chunks, sizeof(int));
	if (!req.numa_ids) {
		dprintf("%s: error: allocating request numa_ids\n",
			"ihk_query_mem");
		ret = -ENOMEM;
		goto out;
	}

	req.num_chunks = num_mem_chunks;

	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: error: ihklib_device_open returned %d\n",
			"ihk_query_mem", fd);
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_QUERY_MEM, &req);
	if (ret) {
		ret = -errno;
		dprintf("%s: error: IHK_DEVICE_QUERY_MEM returned %d\n",
			"ihk_query_mem", -ret);
		goto out;
	}

	for (i = 0; i < num_mem_chunks; i++) {
		mem_chunks[i].size = req.sizes[i];
		mem_chunks[i].numa_node_number = req.numa_ids[i];
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	free(req.sizes);
	free(req.numa_ids);
	return ret;
}

int ref_ihk_release_mem(int index, struct ihk_mem_chunk* mem_chunks, int num_mem_chunks)
{
	int ret, i;
	struct ihk_mem_req req = { 0 };
	int fd = -1;
	struct ihk_mem_chunk *query_mem_chunks = NULL;

	dprintk("%s: enter\n", "ihk_release_mem");

	ret = ref_ihklib_device_readable(index);
	if (ret) {
		goto out;
	}

	if (num_mem_chunks < 0 || num_mem_chunks > IHK_MAX_NUM_MEM_CHUNKS) {
		dprintf("%s: error: invalid # of chunks (%d)\n",
			"ihk_release_mem", num_mem_chunks);
		ret = -EINVAL;
		goto out;
	}

	if (num_mem_chunks != 0 && mem_chunks == NULL) {
		ret = -EFAULT;
		goto out;
	}

	if (num_mem_chunks == 0) {
		ret = 0;
		goto out;
	};

	if (num_mem_chunks < 0) {
		ret = -EINVAL;
		goto out;
	}

	if (mem_chunks[0].size == IHK_SMP_MEM_ALL) {
		/* Special case for releasing all memory */
		num_mem_chunks = ref_ihk_get_num_reserved_mem_chunks(index);

		query_mem_chunks = calloc(num_mem_chunks,
					  sizeof(struct ihk_mem_chunk));
		if (query_mem_chunks == NULL) {
			dprintf("%s: error: allocating memory chunks\n",
				"ihk_release_mem");
			ret = -ENOMEM;
			goto out;
		}

		ret = ref_ihk_query_mem(index, query_mem_chunks, num_mem_chunks);
		if (ret) {
			dprintf("%s: error: ihk_query_mem returned %d\n",
				"ihk_release_mem", ret);
			goto out;
		}

		mem_chunks = query_mem_chunks;
	}

	req.sizes = calloc(num_mem_chunks, sizeof(size_t));
	if (!req.sizes) {
		dprintf("%s: error: allocating request sizes\n",
			"ihk_release_mem");
		ret = -ENOMEM;
		goto out;
	}

	req.numa_ids = calloc(num_mem_chunks, sizeof(int));
	if (!req.numa_ids) {
		dprintf("%s: error: allocating request numa_ids\n",
			"ihk_release_mem");
		ret = -ENOMEM;
		goto out;
	}

	for (i = 0; i < num_mem_chunks; i++) {
		req.sizes[i] = (size_t)mem_chunks[i].size;
		req.numa_ids[i] = mem_chunks[i].numa_node_number;
	}
	req.num_chunks = num_mem_chunks;

	if ((fd = ref_ihklib_device_open(index)) < 0) {
		dprintf("%s: error: ihklib_device_open\n",
			"ihk_release_mem");
		ret = fd;
		goto out;
	}

	ret = ioctl(fd, IHK_DEVICE_RELEASE_MEM, &req);
	if (ret) {
		ret = -errno;
		dprintf("%s: error: IHK_OS_RELEASE_MEM returned %d\n",
			"ihk_release_mem", -ret);
		goto out;
	}

 out:
	if (fd != -1) {
		close(fd);
	}
	free(query_mem_chunks);
	free(req.sizes);
	free(req.numa_ids);
	return ret;
}

int ref_ihk_get_num_os_instances(int index)
{
	int ret;
	DIR *dir = NULL;
	struct dirent *direp;
	int num_os_instances = 0;

	dprintk("%s: enter\n", "ihk_get_num_os_instances");

	/* don't call access() for /dev/mcosN for permission check
	 * for the call not to collide with ihkmond.
	 */
	if (geteuid() != 0) {
		ret = -EACCES;
		goto out;
	}

	dir = opendir(PATH_DEV);
	if (dir == NULL) {
		ret = -errno;
		dprintf("%s: error: opendir returned %d\n",
			"ihk_get_num_os_instances", -ret);
		goto out;
	}

	while ((direp = readdir(dir))) {
		if ((strncmp(direp->d_name,"mcos",4) == 0)) {
			num_os_instances++;
		}
	}
	ret = num_os_instances;
 out:
	if (dir) {
		closedir(dir);
	}
	return ret;
}

int ref_ihk_get_os_instances(int index, int *indices, int _num_os_instances)
{
	int ret;
	DIR *dir = NULL;
	struct dirent *direp;
	int num_os_instances = 0;
	int num_mcos = 0;

	dprintk("%s: enter\n", "ihk_get_os_instances");
	ret = ref_ihklib_device_readable(index);
	if (ret) {
		dprintf("%s: error: ihklib_device_readable returned %d\n",
			"ihk_get_os_instances", ret);
		goto out;
	}

	ret = ref_ihk_get_num_os_instances(index);
	if (ret < 0) {
		dprintf("%s: error: ihk_get_num_os_instances returned %d\n",
			"ihk_get_os_instances", ret);
		goto out;
	}
	num_os_instances = ret;

	if (num_os_instances != _num_os_instances) {
		dprintf("%s: Actual # of OS instances (%d) != "
			"requested (%d)\n",
			"ihk_get_os_instances", num_os_instances, _num_os_instances);
		ret = -EINVAL;
		goto out;
	}

	if (!indices) {
		ret = -EFAULT;
		goto out;
	}

	dir = opendir(PATH_DEV);
	if (dir == NULL) {
		ret = -errno;
		dprintf("%s: error: opendir returned %d\n",
			"ihk_get_os_instances", -ret);
		goto out;
	}

	while ((direp = readdir(dir))) {
		if ((strncmp(direp->d_name, "mcos", 4) == 0)) {
			indices[num_mcos] = atoi(direp->d_name + 4);
			num_mcos++;
		}
	}

	ret = 0;
 out:
	if (dir) {
		closedir(dir);
	}
	return ret;
}
