/* Functional McKernel OS/apps + Rust/assembly only; no security testing.
 * MAP_FIXED replaces only the second page of this process's own new mapping.
 * No XPMEM, file/foreign mapping, protection fault or signal oracle.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <unistd.h>
#if !defined(__x86_64__) || __SIZEOF_POINTER__ != 8
#error selected Linux x86_64 LP64 ABI required
#endif
_Static_assert(sizeof(long) == 8 && sizeof(size_t) == 8 && sizeof(off_t) == 8,
               "selected mmap ABI widths");
int main(void) {
    const size_t page = 4096, bytes = 8192;
    unsigned char *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap owned"); return 1; }
    for (size_t i = 0; i < bytes; ++i) p[i] = (unsigned char)((i * 13u + 17u) & 255u);
    void *q = mmap(p + page, page, PROT_READ | PROT_WRITE,
                   MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (q != p + page) {
        int saved = errno, extra = 0;
        if (q != MAP_FAILED) extra = munmap(q, page);
        int whole = munmap(p, bytes);
        fprintf(stderr, "owned MAP_FIXED result failed errno=%d extra_unmap=%d whole_unmap=%d\n",
                saved, extra, whole);
        return 1;
    }
    int prefix = 1, zero = 1, rw = 1;
    for (size_t i = 0; i < page; ++i) {
        if (p[i] != (unsigned char)((i * 13u + 17u) & 255u)) prefix = 0;
        if (p[page + i] != 0) zero = 0;
    }
    for (size_t i = 0; i < page; ++i) p[page + i] = (unsigned char)((i * 7u + 9u) & 255u);
    for (size_t i = 0; i < page; ++i)
        if (p[page + i] != (unsigned char)((i * 7u + 9u) & 255u)) rw = 0;
    int unmap = munmap(p, bytes);
    if (!prefix || !zero || !rw || unmap) {
        fprintf(stderr, "owned MAP_FIXED checks prefix=%d zero=%d rw=%d unmap=%d\n",
                prefix, zero, rw, unmap);
        return 1;
    }
    puts("mmap_fixed_owned fixed_address=1 preserved_prefix=1 zero_replacement=1 replacement_rw=1 unmapped=1");
    return 0;
}
