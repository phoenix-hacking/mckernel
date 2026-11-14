#define _GNU_SOURCE

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

enum { PAYLOAD = 65553 };
struct exchange { int fd; const unsigned char *send; unsigned char *recv; size_t send_len; size_t recv_len; int ok; };

static int transfer(int fd, const unsigned char *out, size_t out_len, unsigned char *in, size_t in_len) {
    size_t w = 0, r = 0;
    while (w < out_len) { ssize_t n = write(fd, out + w, out_len - w); if (n <= 0) return 0; w += (size_t)n; }
    while (r < in_len) { ssize_t n = read(fd, in + r, in_len - r); if (n <= 0) return 0; r += (size_t)n; }
    return 1;
}
static void *worker(void *arg) { struct exchange *x = arg; x->ok = transfer(x->fd, x->send, x->send_len, x->recv, x->recv_len); return NULL; }

int main(void) {
    int s[2]; if (socketpair(AF_UNIX, SOCK_STREAM, 0, s) != 0) return EXIT_FAILURE;
    unsigned char *a = malloc(PAYLOAD), *b = malloc(PAYLOAD), *ar = malloc(PAYLOAD), *br = malloc(PAYLOAD);
    if (!a || !b || !ar || !br) return EXIT_FAILURE;
    for (size_t i = 0; i < PAYLOAD; ++i) { a[i] = (unsigned char)(i * 13u + 7u); b[i] = (unsigned char)(i * 29u + 3u); }
    struct exchange x = {s[1], b, br, PAYLOAD, PAYLOAD, 0}; pthread_t t;
    if (pthread_create(&t, NULL, worker, &x) != 0) return EXIT_FAILURE;
    int main_ok = transfer(s[0], a, PAYLOAD, ar, PAYLOAD); pthread_join(t, NULL);
    int exact = main_ok && x.ok && memcmp(ar, b, PAYLOAD) == 0 && memcmp(br, a, PAYLOAD) == 0;
    close(s[0]); close(s[1]); free(a); free(b); free(ar); free(br);
    printf("sent=%d received=%d exact=%d valid=%d\n", PAYLOAD, PAYLOAD, exact, exact);
    return exact ? EXIT_SUCCESS : EXIT_FAILURE;
}
