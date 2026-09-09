#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    char path[] = "/tmp/mckernel-offset-XXXXXX"; int fd = mkstemp(path);
    if (fd < 0) return EXIT_FAILURE; unlink(path);
    const char bytes[] = "ABCD"; if (write(fd, bytes, 4) != 4 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    int hand[2]; if (pipe(hand) != 0) return EXIT_FAILURE;
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) {
        char token; if (read(hand[0], &token, 1) != 1) _exit(24);
        char part[2]; ssize_t n = read(fd, part, 2); _exit(n == 2 && part[0] == 'C' && part[1] == 'D' ? 23 : 24);
    }
    char parent_part[2]; ssize_t parent_n = read(fd, parent_part, 2); char token = 'x'; write(hand[1], &token, 1);
    int status = 0; waitpid(child, &status, 0); close(hand[0]); close(hand[1]); close(fd);
    int parent_ok = parent_n == 2 && parent_part[0] == 'A' && parent_part[1] == 'B';
    int child_ok = WIFEXITED(status) && WEXITSTATUS(status) == 23;
    printf("parent=%c%c parent_ok=%d child_offset_ok=%d child_code=%d\n", parent_part[0], parent_part[1], parent_ok, child_ok,
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return (parent_ok && child_ok) ? EXIT_SUCCESS : EXIT_FAILURE;
}
