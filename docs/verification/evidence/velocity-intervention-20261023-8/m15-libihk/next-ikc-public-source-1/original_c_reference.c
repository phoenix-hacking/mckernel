/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <stddef.h>
#include <ihk/ihk_host_user.h>
#define IHK_MAX_NUM_CPUS 1024
#define dprintf(...) ((void)0)
#define eprintf(...) fprintf(stderr,__VA_ARGS__)
#define ikc_str2count ref_ikc_str2count
#define ikc_str2req ref_ikc_str2req
#define ikc_req2str ref_ikc_req2str
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

static int ikc_str2array(char *_ikc_list, int num_maps,
		int *src_cpus, int *dst_cpus)
{
	int ret = 0;
	int i;
	int token_cnt = 0, total_cnt = 0;
	int cpu_buf[IHK_MAX_NUM_CPUS] = {0};
	char *ikc_list, *to_free = NULL;
	char *token;
	char *endp;

	if (!_ikc_list) {
		/* nothing to do */
		ret = 0;
		goto out;
	}

	if (!(ikc_list = strdup(_ikc_list))) {
		ret = -errno;
		dprintf("%s: error: allocating ikc_list\n",
			__func__);
		goto out;
	}
	to_free = ikc_list;

	token = strsep(&ikc_list, "+");
	while (token) {
		char *cpu_list;
		char *ikc_cpu;
		int dst_cpu;

		if (*token == 0) {
			dprintf("%s: error: plus: missing car: %s\n",
				__func__, _ikc_list);
			ret = -EINVAL;
			goto out;
		}

		cpu_list = strsep(&token, ":");
		if (*cpu_list == 0) {
			dprintf("%s: error: colon: missing car: %s\n",
				__func__, _ikc_list);
			ret = -EINVAL;
			goto out;
		}

		if (!token) {
			dprintf("%s: error: colon: not found: %s\n",
				__func__, _ikc_list);
			ret = -EINVAL;
			goto out;
		}

		token_cnt = cpu_str2array(cpu_list, IHK_MAX_NUM_CPUS, cpu_buf);
		if (token_cnt <= 0) {
			dprintf("%s: cpu_str2array failed with %d\n",
				__func__, token_cnt);
			ret = -EINVAL;
			goto out;
		}

		ikc_cpu = token;

		if (*ikc_cpu == 0) {
			dprintf("%s: error: colon: missing cdr: %s\n",
				__func__, _ikc_list);
			ret = -EINVAL;
			goto out;
		}

		dst_cpu = strtol(ikc_cpu, &endp, 10);
		if (*endp != '\0') {
			dprintf("%s: error: illegal expression: %s\n",
				__func__, ikc_cpu);
			ret = -EINVAL;
			goto out;
		}

		/* Store IKC target CPU */
		for (i = 0; i < token_cnt; i++) {
			if (src_cpus && dst_cpus && num_maps > total_cnt) {
				src_cpus[total_cnt] = cpu_buf[i];
				dst_cpus[total_cnt] = dst_cpu;
			}
			total_cnt++;
		}

		token = strsep(&ikc_list, "+");
	}

	ret = total_cnt;

 out:
	free(to_free);
	return ret;
}

int ikc_str2count(char *_ikc_list)
{
	return ikc_str2array(_ikc_list, 0, NULL, NULL);
}

int ikc_str2req(char *_ikc_list, int num_cpus, struct ihk_ikc_req *req)
{
	int ret = 0;

	if (!req) {
		eprintf("%s: error: invalid req pointer (NULL)\n", __func__);
		ret = -EINVAL;
		goto out;
	}

	ret = ikc_str2array(_ikc_list, num_cpus, req->src_cpus, req->dst_cpus);
	req->num_cpus = ret;

 out:
	return ret;
}

char *ikc_req2str(struct ihk_ikc_req *req)
{
	int i, src, dst, max_dst = -1, idx, n = 0;
	char *str = NULL;
	size_t buflen = 64;

	/* Sender-set (sset): Set of senders sharing the same destination */
	int *rank = NULL; /* Order in sender-set, indexed by IKC source CPU# */
	int *ikc_sset_sizes = NULL; /* Indexed by IKC destination CPU# */
	int **ikc_sset_members = NULL; /* Indexed by IKC destination CPU# */

	str = malloc(buflen);
	if (!str) {
		goto out;
	}

	memset(str, 0, buflen);

	rank = calloc(sizeof(int), IHK_MAX_NUM_CPUS);
	if (!rank) {
		eprintf("%s: error: allocating rank\n", __func__);
		goto out;
	}

	ikc_sset_sizes = calloc(sizeof(int), IHK_MAX_NUM_CPUS);
	if (!ikc_sset_sizes) {
		eprintf("%s: error: allocating num_ikc_ssets\n", __func__);
		goto out;
	}

	ikc_sset_members = calloc(sizeof(int *), IHK_MAX_NUM_CPUS);
	if (!ikc_sset_members) {
		eprintf("%s: error: allocating ikc_sset_members\n", __func__);
		goto out;
	}

	for (idx = 0; idx < req->num_cpus; idx++) {
		src = req->src_cpus[idx];
		dst = req->dst_cpus[idx];

		rank[src] = ikc_sset_sizes[dst];
		ikc_sset_sizes[dst]++;
		if (max_dst < dst) {
			max_dst = dst;
		}
	}

	for (idx = 0; idx < req->num_cpus; idx++) {
		src = req->src_cpus[idx];
		dst = req->dst_cpus[idx];

		if (!ikc_sset_members[dst]) {
			ikc_sset_members[dst] = calloc(sizeof(int),
					ikc_sset_sizes[dst]);
			if (!ikc_sset_members[dst]) {
				eprintf("%s: error: allocating ikc_sset_members\n",
					__func__);
				goto out;
			}
		}
		*(ikc_sset_members[dst] + rank[src]) = src;
	}

	for (dst = 0; dst < IHK_MAX_NUM_CPUS; dst++) {
		if (ikc_sset_sizes[dst] == 0) {
			continue;
		}

		for (i = 0; i < ikc_sset_sizes[dst]; i++) {
			n += snprintf_realloc(&str, &buflen, n,
				"%d", *(ikc_sset_members[dst] + i));
			if (i != ikc_sset_sizes[dst] - 1) {
				n += snprintf_realloc(&str, &buflen, n, ",");
			}
		}
		n += snprintf_realloc(&str, &buflen, n, ":%d", dst);
		if (dst != max_dst) {
			n += snprintf_realloc(&str, &buflen, n, "+");
		}
	}

	dprintf("get_ikc_map,query_res=%s\n", str);

out:
	if (ikc_sset_members) {
		for (dst = 0; dst < IHK_MAX_NUM_CPUS; ++dst) {
			free(ikc_sset_members[dst]);
		}
	}

	free(ikc_sset_members);
	free(ikc_sset_sizes);
	free(rank);

	return str;
}
