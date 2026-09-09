#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    const char *link = "/case/work/readlink-025"; const char *target = "target-file"; unlink(link);
    if (symlink(target, link) != 0) return EXIT_FAILURE;
    unsigned char buffer[32]; memset(buffer, 0xcc, sizeof(buffer)); ssize_t n = readlink(link, (char *)buffer + 1, 11);
    int exact = n == 11 && memcmp(buffer + 1, target, 11) == 0; int guards = buffer[0] == 0xcc && buffer[12] == 0xcc;
    printf("read=%zd exact=%d guards=%d\n", n, exact, guards); unlink(link);
    return (exact && guards) ? EXIT_SUCCESS : EXIT_FAILURE;
}
