#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <unistd.h>

int main(void) {
    uint8_t raw[8] = {0};
    int32_t *word = (int32_t *)(raw + 1);

    int rc = (int)syscall(SYS_futex, word, FUTEX_WAIT, 0, NULL, NULL, 0);
    int err = (rc == -1) ? errno : 0;

    printf("futex-wait-unaligned rc=%d errno=%d\n", rc, err);
    printf("raw0=%u raw4=%u\n", raw[0], raw[4]);

    return (rc == -1 && err == EINVAL) ? 0 : 1;
}
