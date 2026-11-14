#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    uint8_t *data = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (data == MAP_FAILED) return EXIT_FAILURE;
    data[0] = 0;
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) { data[0] = 0xc3; _exit(data[0] == 0xc3 ? 23 : 24); }
    data[0] = 0xa5; int status = 0;
    if (waitpid(child, &status, 0) != child) return EXIT_FAILURE;
    int parent_ok = data[0] == 0xa5, child_ok = WIFEXITED(status) && WEXITSTATUS(status) == 23;
    printf("parent_pattern=%d child_exit=%d child_code=%d\n", parent_ok, child_ok,
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    munmap(data, 4096);
    return (parent_ok && child_ok) ? EXIT_SUCCESS : EXIT_FAILURE;
}
