#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char old_path[] = "/case/work/fd-old-XXXXXX", new_path[] = "/case/work/fd-new-XXXXXX";
    int first = mkstemp(old_path), holder = mkstemp(new_path); if (first < 0 || holder < 0) return EXIT_FAILURE;
    if (write(first, "OLD", 3) != 3 || write(holder, "NEW", 3) != 3) return EXIT_FAILURE;
    int old_number = first; close(first); unlink(old_path); close(holder);
    int second = open(new_path, O_RDONLY); if (second < 0) return EXIT_FAILURE;
    char data[4] = {0}; ssize_t n = read(second, data, 3); int new_identity = n == 3 && memcmp(data, "NEW", 3) == 0;
    close(second); unlink(new_path);
    printf("old_fd=%d new_fd=%d fd_reused=%d new_bytes=%d\n", old_number, second, old_number == second, new_identity);
    return (old_number == second && new_identity) ? EXIT_SUCCESS : EXIT_FAILURE;
}
