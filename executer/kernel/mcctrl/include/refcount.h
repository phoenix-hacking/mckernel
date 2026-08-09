/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_REFCOUNT_H
#define _LINUX_REFCOUNT_H

#include <linux/atomic.h>
#include <linux/compiler.h>
#include <linux/spinlock_types.h>

struct mutex;

/**
 * struct refcount_t - variant of atomic_t specialized for reference counts
 * @refs: atomic_t counter field
 *
 * The counter saturates at UINT_MAX and will not move once
 * there. This avoids wrapping the counter and causing 'spurious'
 * use-after-free bugs.
 */
typedef struct refcount_struct {
	atomic_t refs;
} refcount_t;

/**
 * refcount_set - set a refcount's value
 * @r: the refcount
 * @n: value to which the refcount will be set
 */
extern void refcount_set(refcount_t *r, unsigned int n);

/**
 * refcount_read - get a refcount's value
 * @r: the refcount
 *
 * Return: the refcount's value
 */
extern unsigned int refcount_read(const refcount_t *r);
extern __must_check bool refcount_add_not_zero(unsigned int i, refcount_t *r);
extern void refcount_add(unsigned int i, refcount_t *r);
extern __must_check bool refcount_inc_not_zero(refcount_t *r);
extern void refcount_inc(refcount_t *r);
extern __must_check bool refcount_sub_and_test(unsigned int i, refcount_t *r);
extern __must_check bool refcount_dec_and_test(refcount_t *r);
extern void refcount_dec(refcount_t *r);

extern __must_check bool refcount_dec_if_one(refcount_t *r);
extern __must_check bool refcount_dec_not_one(refcount_t *r);
extern __must_check bool refcount_dec_and_mutex_lock(refcount_t *r, struct mutex *lock);
extern __must_check bool refcount_dec_and_lock(refcount_t *r, spinlock_t *lock);
extern __must_check bool refcount_dec_and_lock_irqsave(refcount_t *r,
						       spinlock_t *lock,
						       unsigned long *flags);
#endif /* _LINUX_REFCOUNT_H */
