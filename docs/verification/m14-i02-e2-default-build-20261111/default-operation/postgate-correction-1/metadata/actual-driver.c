#include <linux/module.h>
MODULE_LICENSE("GPL");
unsigned long MAP_KERNEL_START = MODULES_END - (1UL << 23);
