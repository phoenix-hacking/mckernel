/* Functional OS/apps and Rust migration only; no security testing. Original C chain. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <limits.h>
#include <sys/stat.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihklib.h>
#include <ihk/ihk_rusage.h>
#define IHK_SMP_MEM_ALL (-1UL)
#define IHKLIB_LINUX_KMSG_SIZE (4096-256)
#define dprintf(...) do {} while(0)
#define dprintk(...) do {} while(0)
#define dnprintk(...) do {} while(0)
#define CHKANDJUMP(cond,err,...) do {if(cond){ret=err;goto out;}} while(0)
extern int loglevel;
int ref_ihklib_os_open(int);
int ref_mem_str2count(char*);
enum ihklib_os_query_mem_type {IHKLIB_OS_QUERY_MEM_TOTAL,IHKLIB_OS_QUERY_MEM_FREE};
static const char *ihklib_os_query_mem_type_str[]={"MemTotal","MemFree"};
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
static long ref_ihk_memparse(char *token)
{
	long ret;
	char *endp;

	/* "all" or "ALL" indicates best effort allocation */
	if (!strcmp("all", token) || !strcmp("ALL", token)) {
		ret = IHK_SMP_MEM_ALL;
		goto out;
	}

	ret = strtol(token, &endp, 10);

	switch (*endp) {
	case 'e':
	case 'E':
		ret <<= 10;
	case 'p':
	case 'P':
		ret <<= 10;
	case 't':
	case 'T':
		ret <<= 10;
	case 'g':
	case 'G':
		ret <<= 10;
	case 'm':
	case 'M':
		ret <<= 10;
	case 'k':
	case 'K':
		ret <<= 10;
		break;
	case '\0':
		break;
	default:
		ret = -EINVAL;
		break;
	}

out:
	return ret;
}

static int ref_mem_str2array(char *_mem_list, unsigned long *sizes,
			 int *numa_node_numbers)
{
	long ret;
	int mem_count = 0;
	char *mem_list, *to_free = NULL;
	char *token, *cdr;
	char *endp;

	if (!_mem_list) {
		/* nothing to do */
		ret = 0;
		goto out;
	}

	if (!(mem_list = strdup(_mem_list))) {
		ret = -errno;
		dprintf("%s: error: allocating mem_list\n",
			"mem_str2array");
		goto out;
	}
	to_free = mem_list;

	token = strsep(&mem_list, ",");
	while (token) {
		if (*token == 0) {
			dprintf("%s: error: comma: missing car: %s\n",
				"mem_str2array", _mem_list);
			ret = -EINVAL;
			goto out;
		}

		cdr = token;
		token = strsep(&cdr, "@");

		if (cdr && *token == 0) {
			dprintf("%s: error: at-mark: missing car: %s\n",
				"mem_str2array", _mem_list);
			ret = -EINVAL;
			goto out;
		}

		if (cdr && *cdr == 0) {
			dprintf("%s: error: at-mark: missing cdr: %s\n",
				"mem_str2array", _mem_list);
			ret = -EINVAL;
			goto out;
		}

		if (sizes) {
			ret = ref_ihk_memparse(token);
			if (ret < 0 && ret != IHK_SMP_MEM_ALL) {
				dprintf("%s: ihk_memparse failed with %ld\n",
					"mem_str2array", ret);
				goto out;
			}
			sizes[mem_count] = ret;
			if (numa_node_numbers && cdr != NULL) {
				ret = strtol(cdr, &endp, 10);
				if (*endp != '\0') {
					ret = -EINVAL;
					goto out;
				}
				numa_node_numbers[mem_count] = ret;
			}
		}
		mem_count++;

		token = strsep(&mem_list, ",");
	}

	ret = mem_count;

 out:
	free(to_free);
	return ret;
}

int ref_mem_str2count(char *mem_list)
{
	return ref_mem_str2array(mem_list, NULL, NULL);
}

static int ref_mem_str2chunks(char *mem_list, struct ihk_mem_chunk *mem_chunks)
{
	int ret;
	int i;
	int mem_count;
	unsigned long *sizes = NULL;
	int *numa_node_numbers = NULL;

	ret = ref_mem_str2count(mem_list);
	if (ret == 0) {
		return 0;
	}
	if (ret < 0) {
		dprintf("%s: mem_str2count failed with %d\n",
			"mem_str2chunks", ret);
		goto out;
	}
	mem_count = ret;

	sizes = calloc(sizeof(unsigned long), mem_count);
	if (!sizes) {
		ret = -ENOMEM;
		goto out;
	}

	numa_node_numbers = calloc(sizeof(unsigned long), mem_count);
	if (!numa_node_numbers) {
		ret = -ENOMEM;
		goto out;
	}

	ret = ref_mem_str2array(mem_list, sizes, numa_node_numbers);
	if (ret < 0) {
		dprintf("%s: mem_str2array failed with %d\n",
			"mem_str2chunks", ret);
		goto out;
	}

	for (i = 0; i < mem_count; i++) {
		mem_chunks[i].size = sizes[i];
		mem_chunks[i].numa_node_number =
			numa_node_numbers[i];
	}

	ret = 0;
 out:
	free(sizes);
	free(numa_node_numbers);
	return ret;
}

static int ref_get_meminfo_path(char *path, int os_index, int node)
{
	return snprintf(path, PATH_MAX,
			"/sys/devices/virtual/mcos/mcos%d/"
			"sys/devices/system/node/node%d/meminfo",
			os_index, node);
}

int ref_ihklib_os_query_mem_sysfs(int index, char *result, ssize_t sz_result,
			      const char *type)
{
	int ret;
	int node = 0;
	char path[PATH_MAX];
	int len = 0;
	struct stat sb;
	FILE *fp = NULL;

	dprintk("%s: enter\n", "ihklib_os_query_mem_sysfs");

	if (!result || sz_result <= 0 || !type) {
		ret = -EINVAL;
		goto out;
	}

	memset(result, 0, sz_result);

	ref_get_meminfo_path(path, index, node);

	while (stat(path, &sb) != -1) {
		unsigned long free_kb = 0;
		char *line = NULL;
		size_t line_len;

		fp = fopen(path, "r");
		if (fp == NULL) {
			ret = -EINVAL;
			dnprintk(path, "%s: error: opening %s\n",
				 "ihklib_os_query_mem_sysfs", _path);
			goto out;
		}

		while (getline(&line, &line_len, fp) != -1) {
			int scan_node;
			char scanfmt[1024];
			int scanfmt_len;

			scanfmt_len = snprintf(scanfmt, sizeof(scanfmt),
					       "Node %%d %s:%%16lu kB",
					       type);
			if (scanfmt_len >= sizeof(scanfmt)) {
				eprintf("%s: error: type string (%s) is too long\n",
					"ihklib_os_query_mem_sysfs", type);
				ret = -1;
				goto out;
			}

			if (sscanf(line, scanfmt,
				   &scan_node, &free_kb) == 2) {
				if (node > 0)
					len += snprintf(&result[len],
							sz_result - len, ",");

				len += snprintf(&result[len], sz_result - len,
						"%lu@%d",
						free_kb * 1024, node);
			}

			free(line);
			line = NULL;
		}

		fclose(fp);
		fp = NULL;

		++node;
		ref_get_meminfo_path(path, index, node);
	}

	CHKANDJUMP(len == 0, -1, "%s not found\n", type);

	ret = 0;
out:
	if (fp) {
		fclose(fp);
	}
	return ret;
}

static int ref_ihklib_os_query_mem(int index, unsigned long *result,
		 int num_numa_nodes, enum ihklib_os_query_mem_type type)
{
	int i, ret;
	char result_str[16 * IHK_MAX_NUM_NUMA_NODES];
	struct ihk_mem_chunk mem_chunks[IHK_MAX_NUM_NUMA_NODES];
	int num_mem_chunks = num_numa_nodes;
	int fd = -1;

	dprintk("%s: enter\n", "ihklib_os_query_mem");

	if (!result) {
		ret = -EFAULT;
		goto out;
	}

	if ((fd = ref_ihklib_os_open(index)) < 0) {
		eprintf("%s: error: ihklib_os_open\n",
			"ihklib_os_query_mem");
		ret = fd;
		goto out;
	}

	ret = ref_ihklib_os_query_mem_sysfs(index, result_str,
					sizeof(result_str),
					ihklib_os_query_mem_type_str[type]);
	CHKANDJUMP(ret != 0, -EINVAL,
		   "ihklib_os_query_total_mem failed\n");

	num_mem_chunks = ref_mem_str2count(result_str);
	if (num_mem_chunks != num_numa_nodes) {
		ret = -EINVAL;
		eprintf("%s: error: actual # of NUMA nodes (%d) != requested (%d)\n",
			"ihklib_os_query_mem", num_mem_chunks, num_numa_nodes);
		goto out;
	}

	memset(mem_chunks, 0, sizeof(mem_chunks));
	ref_mem_str2chunks(result_str, mem_chunks);

	for (i = 0; i < num_mem_chunks; i++) {
		CHKANDJUMP(mem_chunks[i].numa_node_number >= num_numa_nodes ||
			   mem_chunks[i].numa_node_number < 0, -EINVAL,
			   "NUMA node number out of range\n");
		result[mem_chunks[i].numa_node_number] = mem_chunks[i].size;
	}

	ret = 0;
 out:
	if (fd != -1) {
		close(fd);
	}
	return ret;
}

int ref_ihk_os_query_total_mem(int index, unsigned long *result,
			   int num_numa_nodes)
{
	dprintk("%s: enter\n", "ihk_os_query_total_mem");
	return ref_ihklib_os_query_mem(index, result, num_numa_nodes,
				   IHKLIB_OS_QUERY_MEM_TOTAL);
}

int ref_ihk_os_query_free_mem(int index, unsigned long *result,
		      int num_numa_nodes)
{
	dprintk("%s: enter\n", "ihk_os_query_free_mem");
	return ref_ihklib_os_query_mem(index, result, num_numa_nodes,
				   IHKLIB_OS_QUERY_MEM_FREE);
}
