/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/kobject.h>
#include <linux/sysfs.h>
#include <linux/stddef.h>
#include <asm/page.h>

const unsigned long mckernel_sysfs_layout[]
__attribute__((section(".mckernel_sysfs_layout"), used)) = {
	sizeof(struct kobject), __alignof__(struct kobject),
	offsetof(struct kobject, name), offsetof(struct kobject, parent),
	offsetof(struct kobject, ktype), offsetof(struct kobject, sd),
	offsetof(struct kobject, kref),
	sizeof(struct kobj_type), __alignof__(struct kobj_type),
	offsetof(struct kobj_type, release), offsetof(struct kobj_type, sysfs_ops),
	sizeof(struct attribute), __alignof__(struct attribute),
	offsetof(struct attribute, name), offsetof(struct attribute, mode),
	sizeof(struct kobj_attribute), __alignof__(struct kobj_attribute),
	offsetof(struct kobj_attribute, attr), offsetof(struct kobj_attribute, show),
	offsetof(struct kobj_attribute, store), PAGE_SIZE,
};
