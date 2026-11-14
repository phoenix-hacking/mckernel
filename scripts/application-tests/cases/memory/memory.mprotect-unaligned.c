#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    unsigned char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return EXIT_FAILURE;
    for (size_t i = 0; i < 4096; ++i) p[i] = (unsigned char)((i * 13u + 9u) & 0xffu);
    errno = 77;
    int rc = mprotect(p + 1, 4096, PROT_READ);
    int saved_errno = errno;
    size_t bad = 4096;
    for (size_t i = 0; i < 4096; ++i) if (p[i] != (unsigned char)((i * 13u + 9u) & 0xffu)) { bad = i; break; }
    printf("rc=%d errno=%d bad_index=%zu\n", rc, saved_errno, bad);
    if (munmap(p, 4096) != 0) return EXIT_FAILURE;
    return (rc == -1 && saved_errno == EINVAL && bad == 4096) ? EXIT_SUCCESS : EXIT_FAILURE;
}
