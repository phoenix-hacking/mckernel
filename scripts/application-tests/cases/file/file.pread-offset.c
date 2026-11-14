#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/pread-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char input[32], output[5]; for (size_t i = 0; i < 32; ++i) input[i] = (unsigned char)(0x40u + i);
    if (write(fd, input, 32) != 32 || lseek(fd, 7, SEEK_SET) != 7) return EXIT_FAILURE;
    ssize_t got = pread(fd, output, 5, 11); off_t offset = lseek(fd, 0, SEEK_CUR); size_t bad = 5;
    for (size_t i = 0; i < 5; ++i) if (output[i] != input[11 + i]) { bad = i; break; }
    printf("read=%zd bad_index=%zu offset=%lld\n", got, bad, (long long)offset);
    close(fd); unlink(path); return (got == 5 && bad == 5 && offset == 7) ? EXIT_SUCCESS : EXIT_FAILURE;
}
