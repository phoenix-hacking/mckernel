/*
 * kref.h - library routines for handling generic reference counted objects
 * (based on Linux implementation)
 *
 * This file is released under the GPLv2.
 *
 */

#ifndef _KREF_H_
#define _KREF_H_

#include <ihk/atomic.h>
#include <ihk/lock.h>

/*
 * Bit 30 marks a kref as McKernel internal.
 * This can be used to distinguish krefs from Linux and
 * it also ensures that a non deallocated kref will not
 * crash the Linux allocator.
 */
#define MCKERNEL_KREF_MARK	(1U << 30)

struct kref {
	ihk_atomic_t		refcount;
};

void kref_init(struct kref *kref);
unsigned int kref_read(const struct kref *kref);
unsigned int kref_is_mckernel(const struct kref *kref);
void kref_get(struct kref *kref);
int kref_put(struct kref *kref, void (*release)(struct kref *kref));

#endif /* _KREF_H_ */
