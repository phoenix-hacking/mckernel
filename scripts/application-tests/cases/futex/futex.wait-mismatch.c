#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <unistd.h>

int main(void) {
    int futex_word = 0;
    int expected = 1;
    const long rc = syscall(SYS_futex, (long)&futex_word, FUTEX_WAIT, expected, NULL, NULL, 0);
    int err = (rc == -1) ? errno : 0;

    printf("futex-wait-mismatch rc=%ld errno=%d\n", rc, err);
    printf("word=%d\n", futex_word);
    printf("buffer-end=%d\n", 42);

    return (rc == -1 && err == EAGAIN) ? 0 : 1;
}
