#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/file.h>
#include <unistd.h>

int main(void) {
    char path[] = "/tmp/mckernel-flock-XXXXXX"; int seed = mkstemp(path); if (seed < 0) return EXIT_FAILURE;
    close(seed); int first = open(path, O_RDWR), second = open(path, O_RDWR); unlink(path);
    if (first < 0 || second < 0) return EXIT_FAILURE;
    int first_lock = flock(first, LOCK_EX | LOCK_NB); errno = 0;
    int second_lock = flock(second, LOCK_EX | LOCK_NB); int contention_errno = errno;
    int unlock = flock(first, LOCK_UN); int retry = flock(second, LOCK_EX | LOCK_NB);
    close(first); close(second);
    int blocked = second_lock == -1 && contention_errno == EWOULDBLOCK;
    int valid = first_lock == 0 && blocked && unlock == 0 && retry == 0;
    printf("first=%d second=%d errno=%d blocked=%d unlock=%d retry=%d valid=%d\n", first_lock, second_lock, contention_errno, blocked, unlock, retry, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
