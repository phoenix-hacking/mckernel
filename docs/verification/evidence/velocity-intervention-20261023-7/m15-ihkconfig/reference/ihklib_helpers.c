/* TEST ORACLE ONLY: verbatim narrowly extracted current ihklib helpers. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <ihk/ihklib.h>
#include <ihk/ihklib_private.h>
#define dprintf(...) do {} while (0)
#define eprintf(...) printf(__VA_ARGS__)
#define IHK_SMP_MEM_ALL (-1UL)
static int snprintf_realloc(char **str, size_t *size,
		size_t offset, const char *format, ...)
{
	int ret, needed;
	char *tmp;
	va_list ap;

	va_start(ap, format);
	while (0 <= (ret = vsnprintf(*str + offset, *size - offset,
				format, ap))
		  && *size - offset < (needed = ret + 1)) {
		va_end(ap);

		while (*size - offset < needed) {
			*size *= 2;
		}

		tmp = realloc(*str, *size);

		if (tmp) {
			*str = tmp;
		} else {
			free(*str);
			*str = NULL;
			return -1;
		}
		va_start(ap, format);
	}
	va_end(ap);

	return ret;
}

static int cpu_str2array(char *_cpu_list, int num_cpus, int *cpus)
{
	int ret = 0;
	int i;
	int cpu_rank = 0;
	char *cpu_list, *to_free = NULL;
	char *token, *minus;
	char *endp;

	if (!_cpu_list) {
		/* nothing to do */
		ret = 0;
		goto out;
	}

	if (!(cpu_list = strdup(_cpu_list))) {
		ret = -errno;
		dprintf("%s: error: allocating cpu_list\n",
			__func__);
		goto out;
	}
	to_free = cpu_list;

	token = strsep(&cpu_list, ",");
	while (token) {
		if (*token == 0) {
			dprintf("%s: error: comma: missing car: %s\n",
				__func__, _cpu_list); /* empty token */
			ret = -EINVAL;
			goto out;
		}
		if ((minus = strchr(token, '-'))) {
			int start, end;

			if (*(minus + 1) == 0) {
				dprintf("%s: error: minus: missing cdr: %s\n",
					__func__, _cpu_list); /* empty token */
				ret = -EINVAL;
				goto out;
			}
			*minus = 0;

			start = strtol(token, &endp, 10);
			if (*endp != '\0') {
				ret = -EINVAL;
				goto out;
			}

			end = strtol(minus + 1, &endp, 10);
			if (*endp != '\0') {
				ret = -EINVAL;
				goto out;
			}

			for (i = start; i <= end; i++) {
				if (cpus && num_cpus > cpu_rank) {
					cpus[cpu_rank] = i;
				}
				cpu_rank++;
			}
		}
		else {
			if (cpus && num_cpus > cpu_rank) {
				cpus[cpu_rank] = strtol(token, &endp, 10);
				if (*endp != '\0') {
					ret = -EINVAL;
					goto out;
				}
			}
			cpu_rank++;
		}
		token = strsep(&cpu_list, ",");
	}

	ret = cpu_rank;

 out:
	free(to_free);
	return ret;
}

int cpu_str2count(char *cpu_list)
{
	return cpu_str2array(cpu_list, 0, NULL);
}

int cpu_str2req(char *_cpu_list, int num_cpus, struct ihk_cpu_req *req)
{
	int ret = 0;

	if (!req) {
		eprintf("%s: error: invalid req pointer (NULL)\n", __func__);
		ret = -EINVAL;
		goto out;
	}

	ret = cpu_str2array(_cpu_list, num_cpus, req->cpus);
	req->num_cpus = ret;

 out:
	return ret;
}

static long ihk_memparse(char *token)
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

static int mem_str2array(char *_mem_list, unsigned long *sizes,
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
			__func__);
		goto out;
	}
	to_free = mem_list;

	token = strsep(&mem_list, ",");
	while (token) {
		if (*token == 0) {
			dprintf("%s: error: comma: missing car: %s\n",
				__func__, _mem_list);
			ret = -EINVAL;
			goto out;
		}

		cdr = token;
		token = strsep(&cdr, "@");

		if (cdr && *token == 0) {
			dprintf("%s: error: at-mark: missing car: %s\n",
				__func__, _mem_list);
			ret = -EINVAL;
			goto out;
		}

		if (cdr && *cdr == 0) {
			dprintf("%s: error: at-mark: missing cdr: %s\n",
				__func__, _mem_list);
			ret = -EINVAL;
			goto out;
		}

		if (sizes) {
			ret = ihk_memparse(token);
			if (ret < 0 && ret != IHK_SMP_MEM_ALL) {
				dprintf("%s: ihk_memparse failed with %ld\n",
					__func__, ret);
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

int mem_str2count(char *mem_list)
{
	return mem_str2array(mem_list, NULL, NULL);
}

static int mem_str2chunks(char *mem_list, struct ihk_mem_chunk *mem_chunks)
{
	int ret;
	int i;
	int mem_count;
	unsigned long *sizes = NULL;
	int *numa_node_numbers = NULL;

	ret = mem_str2count(mem_list);
	if (ret == 0) {
		return 0;
	}
	if (ret < 0) {
		dprintf("%s: mem_str2count failed with %d\n",
			__func__, ret);
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

	ret = mem_str2array(mem_list, sizes, numa_node_numbers);
	if (ret < 0) {
		dprintf("%s: mem_str2array failed with %d\n",
			__func__, ret);
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

int mem_str2req(char *mem_list, struct ihk_mem_req *req)
{
	int ret;

	ret = mem_str2count(mem_list);
	if (ret == 0) {
		return 0;
	}
	if (ret < 0) {
		goto out;
	}
	req->num_chunks = ret;

	ret = mem_str2array(mem_list, req->sizes, req->numa_ids);
	if (ret < 0) {
		goto out;
	}

	ret = 0;
 out:
	return ret;
}

static char *cpu_array2str(int num_cpus, int *cpus)
{
	/* prev_cpu should be < -1 so that "if (prev_cpu != cpus[i] - 1)"
	 * won't misunderstand that the cursor is pointing to "0"
	 * following "-1".
	 */
	int i, prev_cpu = -10, in_seq = 0, n = 0;
	size_t buflen = 64;
	char *str = NULL;

	str = malloc(buflen);
	if (!str) {
		goto out;
	}

	memset(str, 0, buflen);

	for (i = 0; i < num_cpus; i++) {
		if (prev_cpu != cpus[i] - 1) {
			if (prev_cpu > 0) {
				n += snprintf_realloc(&str, &buflen, n,
					"%d,", prev_cpu);
			}
			in_seq = 0;
		}
		else {
			if (!in_seq) {
				n += snprintf_realloc(&str, &buflen, n,
					"%d-", prev_cpu);
				in_seq = 1;
			}
		}

		prev_cpu = cpus[i];
	}

	if (prev_cpu >= 0) {
		n += snprintf_realloc(&str, &buflen, n,
			"%d", prev_cpu);
	}

 out:
	return str;
}

char *cpu_req2str(struct ihk_cpu_req *req)
{
	return cpu_array2str(req->num_cpus, req->cpus);
}

static char *mem_array2str(int num_mem_chunks, size_t *sizes, int *numa_ids)
{
	int i, n = 0;
	size_t buflen = 64;
	char *str = NULL;

	str = malloc(buflen);
	if (!str) {
		goto out;
	}

	memset(str, 0, buflen);

	for (i = 0; i < num_mem_chunks; i++) {
		n += snprintf_realloc(&str, &buflen, n,
			"%lu@%d", sizes[i], numa_ids[i]);
		if (i != num_mem_chunks - 1) {
			n += snprintf_realloc(&str, &buflen, n, ",");
		}
	}

 out:
	return str;
}

char *mem_req2str(struct ihk_mem_req *req)
{
	return mem_array2str(req->num_chunks, req->sizes, req->numa_ids);
}

int _ihk_reserve_cpu_str(int dev_index, char *list, char *err_msg)
{
	int ret;
	int num_cpus;
	int *cpus = NULL;

	num_cpus = cpu_str2count(list);
	if (num_cpus <= 0) {
		ret = -EINVAL;
		goto out;
	}

	cpus = calloc(sizeof(int), num_cpus);
	if (!cpus) {
		ret = -ENOMEM;
		goto out;
	}

	ret = cpu_str2array(list, num_cpus, cpus);
	if (ret < 0) {
		ret = -EINVAL;
		goto out;
	}

	ret = ihk_reserve_cpu(dev_index, cpus, num_cpus);
	if (ret) {
		if (err_msg) {
			sprintf(err_msg,
				"%s:%d: ihk_reserve_cpu failed with %d\n",
				__FILE__, __LINE__, ret);
		}
		goto out;
	}
 out:
	free(cpus);
	return ret;
}

int _ihk_reserve_mem_str(int dev_index, char *list, char *err_msg)
{
	int ret;
	int num_mems;
	struct ihk_mem_chunk *mems = NULL;
	int i;

	num_mems = mem_str2count(list);
	if (num_mems <= 0) {
		ret = -EINVAL;
		goto out;
	}

	mems = calloc(sizeof(struct ihk_mem_chunk), num_mems);
	if (!mems) {
		ret = -ENOMEM;
		goto out;
	}

	ret = mem_str2chunks(list, mems);
	if (ret < 0) {
		dprintf("%s: mem_str2chunks failed with %d\n",
			__func__, ret);
		goto out;
	}

	for (i = 0; i < num_mems; i++) {
		dprintf("%s: %lx@%d\n",
			__func__, mems[i].size,
			mems[i].numa_node_number);
	}

	ret = ihk_reserve_mem(dev_index, mems, num_mems);
	if (ret) {
		if (err_msg) {
			sprintf(err_msg,
				"%s:%d: ihk_reserve_mem failed with %d\n",
				__FILE__, __LINE__, ret);
		}
		goto out;
	}

 out:
	free(mems);
	return ret;
}
