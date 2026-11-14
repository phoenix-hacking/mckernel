#define _GNU_SOURCE

#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE; struct pollfd fd = {.fd = p[0], .events = POLLIN};
    int before = poll(&fd, 1, 0); if (write(p[1], "DATA", 4) != 4) return EXIT_FAILURE;
    fd.revents = 0; int after = poll(&fd, 1, 1000); char data[5] = {0}; ssize_t n = read(p[0], data, 4);
    close(p[0]); close(p[1]);
    printf("before=%d after=%d pollin=%d read=%zd data=%s\n", before, after, (fd.revents & POLLIN) != 0, n, data);
    return (before == 0 && after == 1 && (fd.revents & POLLIN) && n == 4 && strcmp(data, "DATA") == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
