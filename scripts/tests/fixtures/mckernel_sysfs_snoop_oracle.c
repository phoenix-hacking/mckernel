/* SPDX-License-Identifier: GPL-2.0-only */
/* Separate verification module; never linked into a production module. */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/types.h>
typedef void *ihk_device_t;
struct sysfsm_ops;
struct sysfsm_node { long client_instance; };

/* Exact old parameter declaration, two bitmap wrappers and eight show bodies. */
#include "native-sysfs-snoop-reference.h"

long mckernel_sysfs_snoop_oracle(unsigned long operation, void *data,
                               int bits, int bytes, char *output, size_t size);
long mckernel_sysfs_snoop_oracle(unsigned long operation, void *data,
                               int bits, int bytes, char *output, size_t size)
{
    struct remote_snooping_param param = { .nbits = bits, .size = bytes, .ptr = data };
    struct sysfsm_node node = { .client_instance = (long)&param };
    switch (operation) {
    case 1: return snooping_remote_show_d32(NULL, &node, output, size);
    case 2: return snooping_remote_show_d64(NULL, &node, output, size);
    case 3: return snooping_remote_show_u32(NULL, &node, output, size);
    case 4: return snooping_remote_show_u64(NULL, &node, output, size);
    case 5: return snooping_remote_show_s(NULL, &node, output, size);
    case 6: return snooping_remote_show_pbl(NULL, &node, output, size);
    case 7: return snooping_remote_show_pb(NULL, &node, output, size);
    case 8: return snooping_remote_show_u32K(NULL, &node, output, size);
    default: return -EINVAL;
    }
}
EXPORT_SYMBOL_GPL(mckernel_sysfs_snoop_oracle);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Unchanged legacy remote snooping bodies, verification only");
