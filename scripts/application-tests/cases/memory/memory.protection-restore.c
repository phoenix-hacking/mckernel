#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    unsigned char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return EXIT_FAILURE;
    p[0] = 0x11;
    int ro = mprotect(p, 4096, PROT_READ);
    int rw = mprotect(p, 4096, PROT_READ | PROT_WRITE);
    for (size_t i = 0; i < 4096; ++i) p[i] = (unsigned char)((i * 23u + 3u) & 0xffu);
    size_t bad = 4096;
    for (size_t i = 0; i < 4096; ++i) if (p[i] != (unsigned char)((i * 23u + 3u) & 0xffu)) { bad = i; break; }
    printf("readonly_rc=%d restore_rc=%d bad_index=%zu\n", ro, rw, bad);
    if (munmap(p, 4096) != 0) return EXIT_FAILURE;
    return (ro == 0 && rw == 0 && bad == 4096) ? EXIT_SUCCESS : EXIT_FAILURE;
}
