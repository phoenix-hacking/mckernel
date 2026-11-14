#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void) {
    int s[2]; if (socketpair(AF_UNIX, SOCK_STREAM, 0, s) != 0) return EXIT_FAILURE;
    const char left[] = "LEFT"; const char right[] = "R"; char buf[8] = {0};
    ssize_t w = write(s[0], left, sizeof(left) - 1); if (w != (ssize_t)(sizeof(left) - 1) || shutdown(s[0], SHUT_WR) != 0) return EXIT_FAILURE;
    ssize_t n = read(s[1], buf, sizeof(buf)); int buffered = n == (ssize_t)(sizeof(left) - 1) && memcmp(buf, left, sizeof(left) - 1) == 0;
    ssize_t eof = read(s[1], buf, sizeof(buf)); int saw_eof = eof == 0;
    ssize_t back = write(s[1], right, 1); char reply = 0; ssize_t got = read(s[0], &reply, 1);
    int reverse = back == 1 && got == 1 && reply == 'R'; int valid = buffered && saw_eof && reverse;
    close(s[0]); close(s[1]);
    printf("buffered=%d eof=%d reverse=%d valid=%d\n", buffered, saw_eof, reverse, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
