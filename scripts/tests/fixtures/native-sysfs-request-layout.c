/* SPDX-License-Identifier: GPL-2.0-only */
#include <stddef.h>
#include <stdio.h>
#include "../../../executer/kernel/mcctrl/sysfs_msg.h"
#define ROW(type) printf("%zu %zu %zu %zu %zu\n", sizeof(struct type), \
    _Alignof(struct type), offsetof(struct type, error), \
    offsetof(struct type, path), offsetof(struct type, busy))
int main(void)
{
    ROW(sysfs_req_create_param);
    ROW(sysfs_req_mkdir_param);
    ROW(sysfs_req_symlink_param);
    ROW(sysfs_req_lookup_param);
    ROW(sysfs_req_unlink_param);
    printf("%zu %zu %zu %zu %zu %zu %zu\n",
        offsetof(struct sysfs_req_create_param, mode),
        offsetof(struct sysfs_req_create_param, client_ops),
        offsetof(struct sysfs_req_create_param, client_instance),
        offsetof(struct sysfs_req_mkdir_param, handle),
        offsetof(struct sysfs_req_symlink_param, target),
        offsetof(struct sysfs_req_lookup_param, handle),
        offsetof(struct sysfs_req_unlink_param, flags));
    return 0;
}
