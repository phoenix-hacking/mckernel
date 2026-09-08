/* SPDX-License-Identifier: GPL-2.0-only */
#include <stddef.h>
#include <stdio.h>
#include "../../../executer/kernel/mcctrl/sysfs_msg.h"
int main(void)
{
    printf("%zu %zu %zu %zu %zu %zu\n", sizeof(struct sysfs_req_setup_param),
        _Alignof(struct sysfs_req_setup_param), offsetof(struct sysfs_req_setup_param, error),
        offsetof(struct sysfs_req_setup_param, buf_rpa), offsetof(struct sysfs_req_setup_param, bufsize),
        offsetof(struct sysfs_req_setup_param, busy));
    return 0;
}
