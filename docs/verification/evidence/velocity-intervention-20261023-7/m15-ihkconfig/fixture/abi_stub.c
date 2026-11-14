/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * TEST ONLY. All device-facing calls are --wrap symbols; never real /dev access.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <ihk/ihklib.h>
_Static_assert(sizeof(struct ihk_cpu_req) == 16, "cpu size");
_Static_assert(offsetof(struct ihk_cpu_req, num_cpus) == 8, "cpu count offset");
_Static_assert(sizeof(struct ihk_mem_req) == 32, "mem size");
_Static_assert(offsetof(struct ihk_mem_req, timeout) == 28, "mem timeout offset");
_Static_assert(sizeof(struct ihk_mem_chunk) == 16, "mem chunk size");
_Static_assert(offsetof(struct ihk_mem_chunk, numa_node_number) == 8, "mem node offset");
static long setting(const char *name, long fallback) {
    const char *v = getenv(name); return v ? strtol(v, NULL, 0) : fallback;
}
static void trace(const char *fmt, ...) {
    const char *p = getenv("IHK_FIXTURE_TRACE");
    if (!p) abort();
    FILE *f = fopen(p, "a"); if (!f) abort();
    va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fputc('\n', f); fclose(f);
}
static int io_result(void) {
    int r = setting("IHK_FIXTURE_IOCTL_RET", 0); if (r < 0) errno = EIO; return r;
}
int __wrap_open(const char *path, int flags, ...) {
    trace("open %s flags=%d", path, flags);
    if (setting("IHK_FIXTURE_FAIL_OPEN", 0)) { errno = ENOENT; return -1; }
    return 17;
}
int __wrap_close(int fd) { trace("close %d", fd); return 0; }
int __wrap_ioctl(int fd, unsigned long request, ...) {
    trace("ioctl fd=%d request=%lx", fd, request);
    va_list ap; va_start(ap, request);
    if (setting("IHK_FIXTURE_FAIL_REQUEST", -1) == (long)request) {
        va_end(ap); errno = EIO; return -1;
    }
    int r = io_result();
    if (request == IHK_DEVICE_GET_NUM_CPUS) { va_end(ap); return r ? r : setting("IHK_FIXTURE_CPU_COUNT", 3); }
    if (request == IHK_DEVICE_CREATE_OS || request == IHK_DEVICE_DESTROY_OS ||
        request == IHK_DEVICE_DEBUG_START || request == IHK_DEVICE_DEBUG_START + 1) {
        trace("integer_arg=%d", va_arg(ap, int));
    } else if (request == IHK_DEVICE_GET_BUILDID) {
        char *out = va_arg(ap, char *); if (!r) {
            if (setting("IHK_FIXTURE_BUILDID_NO_NUL", 0)) memset(out, 'x', sizeof("fixture-build"));
            else strcpy(out, "fixture-build");
        }
    } else if (request == IHK_DEVICE_QUERY_CPU) {
        struct ihk_cpu_req *q = va_arg(ap, struct ihk_cpu_req *);
        trace("cpu_query count=%d", q->num_cpus);
        if (!r && q->cpus) {
            for (int i = 0; i < q->num_cpus; ++i) q->cpus[i] = i;
            if (setting("IHK_FIXTURE_CPU_GAPPED", 0) && q->num_cpus > 1) q->cpus[1] = 3;
        }
    } else if (request == IHK_DEVICE_RELEASE_CPU) {
        struct ihk_cpu_req *q = va_arg(ap, struct ihk_cpu_req *);
        trace("cpu_release count=%d", q->num_cpus);
        for (int i = 0; i < q->num_cpus; ++i) trace("cpu[%d]=%d", i, q->cpus[i]);
    } else if (request == IHK_DEVICE_QUERY_MEM) {
        struct ihk_mem_req *q = va_arg(ap, struct ihk_mem_req *);
        trace("mem_query count=%d sizes=%d nodes=%d", q->num_chunks, !!q->sizes, !!q->numa_ids);
        if (!r) {
            if (!q->sizes) q->num_chunks = setting("IHK_FIXTURE_MEM_COUNT", 2);
            else for (int i = 0; i < q->num_chunks; ++i) { q->sizes[i] = 4096UL << i; q->numa_ids[i] = i; }
        }
    } else if (request == IHK_DEVICE_RELEASE_MEM) {
        struct ihk_mem_req *q = va_arg(ap, struct ihk_mem_req *);
        trace("mem_release count=%d min=%d ratio=%d timeout=%d", q->num_chunks, q->min_chunk_size, q->max_size_ratio_all, q->timeout);
        for (int i = 0; i < q->num_chunks; ++i) trace("mem[%d]=%zu@%d", i, q->sizes[i], q->numa_ids[i]);
    } else { trace("raw_arg=%lx", va_arg(ap, unsigned long)); }
    va_end(ap); if (r < 0) errno = EIO; return r;
}
ssize_t __wrap_pread(int fd, void *buf, size_t size, off_t off) {
    trace("pread fd=%d size=%zu off=%ld", fd, size, (long)off);
    if (setting("IHK_FIXTURE_FAIL_PREAD", 0)) { errno = EIO; return -1; }
    size_t count = setting("IHK_FIXTURE_PREAD_COUNT", size);
    if (count > size) abort();
    for (size_t i = 0; i < count; ++i) ((unsigned char *)buf)[i] = i;
    return count;
}
ssize_t __wrap_pwrite(int fd, const void *buf, size_t size, off_t off) {
    trace("pwrite fd=%d size=%zu off=%ld value=%u", fd, size, (long)off, *(const unsigned *)buf);
    if (setting("IHK_FIXTURE_FAIL_PWRITE", 0)) { errno = EIO; return -1; }
    return setting("IHK_FIXTURE_PWRITE_COUNT", (long)size);
}
static union { unsigned long align; unsigned char bytes[4096]; } mapping;
void *__wrap_mmap(void *p, size_t size, int prot, int flags, int fd, off_t off) {
    trace("mmap null=%d size=%zu prot=%d flags=%d fd=%d off=%ld", !p, size, prot, flags, fd, (long)off);
    if (setting("IHK_FIXTURE_FAIL_MMAP", 0)) { errno = EIO; return (void *)-1; }
    for (size_t i = 0; i < sizeof(mapping.bytes); ++i) mapping.bytes[i] = i;
    return mapping.bytes;
}
int __wrap_munmap(void *p, size_t size) {
    if (p != mapping.bytes) abort();
    trace("munmap size=%zu first=%u", size, *(unsigned *)p); return 0;
}
int ihk_reserve_cpu(int index, int *cpus, int count) {
    trace("ihk_reserve_cpu index=%d count=%d", index, count);
    for (int i = 0; i < count; ++i) trace("cpu[%d]=%d", i, cpus[i]);
    return setting("IHK_FIXTURE_LIB_RET", 0);
}
int ihk_reserve_mem(int index, struct ihk_mem_chunk *m, int count) {
    trace("ihk_reserve_mem index=%d count=%d", index, count);
    for (int i = 0; i < count; ++i) trace("mem[%d]=%lu@%d", i, m[i].size, m[i].numa_node_number);
    return setting("IHK_FIXTURE_LIB_RET", 0);
}
int ihk_get_num_os_instances(int index) {
    trace("ihk_get_num_os_instances index=%d", index); return setting("IHK_FIXTURE_OS_COUNT", 2);
}
int ihk_get_os_instances(int index, int *indices, int count) {
    trace("ihk_get_os_instances index=%d count=%d", index, count);
    for (int i = 0; i < count; ++i) indices[i] = 2 + 5 * i;
    return setting("IHK_FIXTURE_LIB_RET", 0);
}
void *__real_calloc(size_t, size_t);
void *__real_malloc(size_t);
void *__real_realloc(void *, size_t);
char *__real_strdup(const char *);
static int calloc_calls, malloc_calls, realloc_calls, strdup_calls;
void *__wrap_calloc(size_t n, size_t size) {
    if (++calloc_calls == setting("IHK_FIXTURE_FAIL_CALLOC", -1) ||
        (size && n > 1048576 / size)) { errno = ENOMEM; return NULL; }
    return __real_calloc(n, size);
}
void *__wrap_malloc(size_t size) {
    if (++malloc_calls == setting("IHK_FIXTURE_FAIL_MALLOC", -1) || size > 1048576) { errno = ENOMEM; return NULL; }
    return __real_malloc(size);
}
void *__wrap_realloc(void *p, size_t size) {
    if (++realloc_calls == setting("IHK_FIXTURE_FAIL_REALLOC", -1) || size > 1048576) { errno = ENOMEM; return NULL; }
    return __real_realloc(p, size);
}
char *__wrap_strdup(const char *s) {
    if (++strdup_calls == setting("IHK_FIXTURE_FAIL_STRDUP", -1)) { errno = ENOMEM; return NULL; }
    return __real_strdup(s);
}
