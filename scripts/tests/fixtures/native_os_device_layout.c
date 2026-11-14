/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/device.h>
#include <linux/stddef.h>

const unsigned long mckernel_os_device_layout[]
__attribute__((section(".mckernel_os_device_layout"), used)) = {
	sizeof(struct device), __alignof__(struct device),
	offsetof(struct device, kobj),
};
