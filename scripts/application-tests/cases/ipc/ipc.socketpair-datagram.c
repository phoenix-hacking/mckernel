#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void) {
    int s[2]; if (socketpair(AF_UNIX, SOCK_DGRAM, 0, s) != 0) return EXIT_FAILURE;
    const char *m1 = "A", *m2 = "BC", *m3 = "DEF"; char b[8] = {0};
    ssize_t w1 = send(s[0], m1, 1, 0), w2 = send(s[0], m2, 2, 0), w3 = send(s[0], m3, 3, 0);
    ssize_t r1 = recv(s[1], b, sizeof(b), 0); int e1 = r1 == 1 && memcmp(b, m1, 1) == 0;
    ssize_t r2 = recv(s[1], b, sizeof(b), 0); int e2 = r2 == 2 && memcmp(b, m2, 2) == 0;
    ssize_t r3 = recv(s[1], b, sizeof(b), 0); int e3 = r3 == 3 && memcmp(b, m3, 3) == 0;
    close(s[0]); close(s[1]); int valid = w1 == 1 && w2 == 2 && w3 == 3 && e1 && e2 && e3;
    printf("lengths=%zd,%zd,%zd boundaries=%d,%d,%d valid=%d\n", r1, r2, r3, e1, e2, e3, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
