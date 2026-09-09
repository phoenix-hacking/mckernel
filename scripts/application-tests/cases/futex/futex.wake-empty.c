#include <errno.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <unistd.h>

int main(void) {
    int futex_word = 0;
    int rc = (int)syscall(SYS_futex, (long)&futex_word, FUTEX_WAKE, 1, NULL, NULL, 0);
    int err = (rc == -1) ? errno : 0;

    printf("futex-wake-empty rc=%d errno=%d\n", rc, err);
    printf("word=%d guard=%d\n", futex_word, 0xA5);

    return (rc == 0 && err == 0) ? 0 : 1;
}
