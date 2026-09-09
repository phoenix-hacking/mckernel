#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char src_path[] = "/case/work/dup2-src-XXXXXX", dst_path[] = "/case/work/dup2-dst-XXXXXX";
    int src = mkstemp(src_path), dst = mkstemp(dst_path); if (src < 0 || dst < 0) return EXIT_FAILURE;
    if (write(src, "SOURCE", 6) != 6 || write(dst, "TARGET", 6) != 6 || lseek(src, 2, SEEK_SET) != 2) return EXIT_FAILURE;
    if (dup2(src, dst) != dst) return EXIT_FAILURE;
    char got[3] = {0}; ssize_t n = read(dst, got, 2);
    int old_target[6]; int check = open(dst_path, O_RDONLY); if (check < 0 || read(check, old_target, 6) != 6) return EXIT_FAILURE;
    int target_unchanged = memcmp(old_target, "TARGET", 6) == 0; int source_slice = n == 2 && memcmp(got, "UR", 2) == 0;
    printf("read=%zd source_slice=%d target_unchanged=%d\n", n, source_slice, target_unchanged);
    close(check); close(dst); close(src); unlink(src_path); unlink(dst_path);
    return (source_slice && target_unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
