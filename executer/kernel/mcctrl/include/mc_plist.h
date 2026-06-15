/* This is copy of the necessary part from McKernel, for uti-futex */

/*
 * Descending-priority-sorted double-linked list
 *
 * (C) 2002-2003 Intel Corp
 * Inaky Perez-Gonzalez <inaky.perez-gonzalez@intel.com>.
 *
 * 2001-2005 (c) MontaVista Software, Inc.
 * Daniel Walker <dwalker@mvista.com>
 *
 * (C) 2005 Thomas Gleixner <tglx@linutronix.de>
 *
 * Simplifications of the original code by
 * Oleg Nesterov <oleg@tv-sign.ru>
 *
 * Licensed under the FSF's GNU Public License v2 or later.
 *
 * Based on simple lists (include/linux/list.h).
 *
 * This is a priority-sorted list of nodes; each node has a
 * priority from INT_MIN (highest) to INT_MAX (lowest).
 *
 * Addition is O(K), removal is O(1), change of priority of a node is
 * O(K) and K is the number of RT priority levels used in the system.
 * (1 <= K <= 99)
 *
 * This list is really a list of lists:
 *
 *  - The tier 1 list is the prio_list, different priority nodes.
 *
 *  - The tier 2 list is the node_list, serialized nodes.
 *
 * Simple ASCII art explanation:
 *
 * |HEAD          |
 * |              |
 * |prio_list.prev|<------------------------------------|
 * |prio_list.next|<->|pl|<->|pl|<--------------->|pl|<-|
 * |10            |   |10|   |21|   |21|   |21|   |40|   (prio)
 * |              |   |  |   |  |   |  |   |  |   |  |
 * |              |   |  |   |  |   |  |   |  |   |  |
 * |node_list.next|<->|nl|<->|nl|<->|nl|<->|nl|<->|nl|<-|
 * |node_list.prev|<------------------------------------|
 *
 * The nodes on the prio_list list are sorted by priority to simplify
 * the insertion of new nodes. There are no nodes with duplicate
 * priorites on the list.
 *
 * The nodes on the node_list are ordered by priority and can contain
 * entries which have the same priority. Those entries are ordered
 * FIFO
 *
 * Addition means: look for the prio_list node in the prio_list
 * for the priority of the node and insert it before the node_list
 * entry of the next prio_list node. If it is the first node of
 * that priority, add it to the prio_list in the right position and
 * insert it into the serialized node_list list
 *
 * Removal means remove it from the node_list and remove it from
 * the prio_list if the node_list list_head is non empty. In case
 * of removal from the prio_list it must be checked whether other
 * entries of the same priority are on the list or not. If there
 * is another entry of the same priority then this entry has to
 * replace the removed entry on the prio_list. If the entry which
 * is removed is the only entry of this priority then a simple
 * remove from both list is sufficient.
 *
 * INT_MIN is the highest priority, 0 is the medium highest, INT_MAX
 * is lowest priority.
 *
 * No locking is done, up to the caller.
 *
 */
#ifndef _MC_PLIST_H_
#define _MC_PLIST_H_

#include <arch-lock.h>

struct mc_plist_head {
	struct list_head prio_list;
	struct list_head node_list;
#ifdef CONFIG_DEBUG_PI_LIST
	raw_spinlock_t *rawlock;
	spinlock_t *spinlock;
#endif
};

struct mc_plist_node {
	int			prio;
	struct mc_plist_head	plist;
};

/**
 * plist_head_init - dynamic struct plist_head initializer
 * @head:	&struct plist_head pointer
 * @lock:	spinlock protecting the list (debugging)
 */
extern void mc_plist_head_init(struct mc_plist_head *head,
		_ihk_spinlock_t *lock);

/**
 * plist_head_init_raw - dynamic struct plist_head initializer
 * @head:	&struct plist_head pointer
 * @lock:	raw_spinlock protecting the list (debugging)
 */
extern void mc_plist_head_init_raw(struct mc_plist_head *head,
		_ihk_spinlock_t *lock);

/**
 * plist_node_init - Dynamic struct plist_node initializer
 * @node:	&struct plist_node pointer
 * @prio:	initial node priority
 */
extern void mc_plist_node_init(struct mc_plist_node *node, int prio);

extern void mc_plist_add(struct mc_plist_node *node,
		struct mc_plist_head *head);
extern void mc_plist_del(struct mc_plist_node *node,
		struct mc_plist_head *head);

/**
 * plist_head_empty - return !0 if a plist_head is empty
 * @head:	&struct plist_head pointer
 */
extern int mc_plist_head_empty(const struct mc_plist_head *head);

/**
 * plist_node_empty - return !0 if plist_node is not on a list
 * @node:	&struct plist_node pointer
 */
extern int mc_plist_node_empty(const struct mc_plist_node *node);

/* All functions below assume the plist_head is not empty. */

/**
 * plist_first - return the first node (and thus, highest priority)
 * @head:	the &struct plist_head pointer
 *
 * Assumes the plist is _not_ empty.
 */
extern struct mc_plist_node *mc_plist_first(const struct mc_plist_head *head);

#endif
