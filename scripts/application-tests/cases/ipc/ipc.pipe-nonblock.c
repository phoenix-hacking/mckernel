#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0 || fcntl(p[0], F_SETFL, fcntl(p[0], F_GETFL) | O_NONBLOCK) != 0) return EXIT_FAILURE;
    char buffer[3] = {0xa5, 0xa5, 0}; errno = 0; ssize_t first = read(p[0], buffer, 2); int first_errno = errno;
    int unchanged_first = buffer[0] == 0xa5 && buffer[1] == 0xa5;
    if (write(p[1], "OK", 2) != 2) return EXIT_FAILURE; ssize_t later = read(p[0], buffer, 2); int exact = later == 2 && buffer[0] == 'O' && buffer[1] == 'K';
    close(p[0]); close(p[1]);
    printf("first=%zd errno=%d eagain=%d unchanged=%d later=%zd data=%c%c exact=%d\n", first, first_errno,
           first_errno == EAGAIN, unchanged_first, later, buffer[0], buffer[1], exact);
    return (first == -1 && first_errno == EAGAIN && later == 2 && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
