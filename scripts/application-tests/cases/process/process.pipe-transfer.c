#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

enum { TOTAL = 65553 };
static unsigned char pattern(unsigned i) { return (unsigned char)(i % 251u); }

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE;
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) {
        close(p[0]); unsigned char buf[4096];
        for (unsigned sent = 0; sent < TOTAL;) {
            unsigned n = TOTAL - sent < sizeof(buf) ? TOTAL - sent : sizeof(buf);
            for (unsigned i = 0; i < n; ++i) buf[i] = pattern(sent + i);
            for (unsigned off = 0; off < n;) { ssize_t w = write(p[1], buf + off, n - off); if (w <= 0) _exit(24); off += (unsigned)w; }
            sent += n;
        }
        close(p[1]); _exit(0);
    }
    close(p[1]); unsigned char buf[4096]; unsigned received = 0; int content_ok = 1; ssize_t n;
    while ((n = read(p[0], buf, sizeof(buf))) > 0) {
        for (ssize_t i = 0; i < n; ++i) if (received + (unsigned)i >= TOTAL || buf[i] != pattern(received + (unsigned)i)) content_ok = 0;
        received += (unsigned)n;
    }
    close(p[0]); int status = 0; waitpid(child, &status, 0);
    int eof = n == 0, child_ok = WIFEXITED(status) && WEXITSTATUS(status) == 0;
    printf("bytes=%u content_ok=%d eof=%d child_ok=%d\n", received, content_ok, eof, child_ok);
    return (received == TOTAL && content_ok && eof && child_ok) ? EXIT_SUCCESS : EXIT_FAILURE;
}
