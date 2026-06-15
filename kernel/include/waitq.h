/**
 * \file waitq.h
 * License details are found in the file LICENSE.
 *  
 * \brief
 * Waitqueue adaptation from Sandia's Kitten OS 
 * (originally taken from Linux)
 *
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * Copyright (C) 2012  RIKEN AICS
 *
 */

#ifndef _LWK_WAITQ_H
#define _LWK_WAITQ_H

/* Kitten waitqueue adaptation */

#include <ihk/lock.h>
#include <list.h>

struct thread;
struct waitq_entry;

typedef int (*waitq_func_t)(struct waitq_entry *wait, unsigned mode,
							int flags, void *key);

int default_wake_function(struct waitq_entry *wait, unsigned mode, int flags,
			              void *key);
int locked_wake_function(struct waitq_entry *wait, unsigned mode, int flags,
			              void *key);

typedef struct waitq {
	ihk_spinlock_t lock;
	struct list_head waitq;
} waitq_t;

#define WQ_FLAG_EXCLUSIVE       0x01

typedef struct waitq_entry {
	struct list_head link;
	void *private;
	unsigned int flags;
	waitq_func_t func;
} waitq_entry_t;

extern void waitq_init(waitq_t *waitq);
extern void waitq_init_entry(waitq_entry_t *entry, struct thread *proc);
extern void waitq_init_locked_entry(waitq_entry_t *entry, struct thread *proc);
extern int waitq_active(waitq_t *waitq);
extern void waitq_add_entry(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_add_entry_locked(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_prepare_to_wait(waitq_t *waitq, 
                                  waitq_entry_t *entry, int state);
extern void waitq_finish_wait(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_wakeup(waitq_t *waitq);
extern int waitq_wake_nr(waitq_t *waitq, int nr);
extern int waitq_wake_nr_locked(waitq_t *waitq, int nr);
extern void waitq_remove_entry(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_remove_entry_locked(waitq_t *waitq, waitq_entry_t *entry);

#endif
