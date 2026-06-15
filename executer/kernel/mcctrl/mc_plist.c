/* This is copy of the necessary part from McKernel, for uti-futex */

#include <mc_plist.h>
#include <arch-lock.h>

#ifdef CONFIG_DEBUG_PI_LIST

static void mc_plist_check_prev_next(struct list_head *t, struct list_head *p,
				  struct list_head *n)
{
	WARN(n->prev != p || p->next != n,
			"top: %p, n: %p, p: %p\n"
			"prev: %p, n: %p, p: %p\n"
			"next: %p, n: %p, p: %p\n",
			 t, t->next, t->prev,
			p, p->next, p->prev,
			n, n->next, n->prev);
}

static void mc_plist_check_list(struct list_head *top)
{
	struct list_head *prev = top, *next = top->next;

	mc_plist_check_prev_next(top, prev, next);
	while (next != top) {
		prev = next;
		next = prev->next;
		mc_plist_check_prev_next(top, prev, next);
	}
}

static void mc_plist_check_head(struct mc_plist_head *head)
{
	WARN_ON(!head->rawlock && !head->spinlock);
	if (head->rawlock)
		WARN_ON_SMP(!raw_spin_is_locked(head->rawlock));
	if (head->spinlock)
		WARN_ON_SMP(!spin_is_locked(head->spinlock));
	mc_plist_check_list(&head->prio_list);
	mc_plist_check_list(&head->node_list);
}

#else
# define mc_plist_check_head(h)	do { } while (0)
#endif

void mc_plist_head_init(struct mc_plist_head *head, _ihk_spinlock_t *lock)
{
	INIT_LIST_HEAD(&head->prio_list);
	INIT_LIST_HEAD(&head->node_list);
#ifdef CONFIG_DEBUG_PI_LIST
	head->spinlock = lock;
	head->rawlock = NULL;
#endif
}

void mc_plist_head_init_raw(struct mc_plist_head *head, _ihk_spinlock_t *lock)
{
	INIT_LIST_HEAD(&head->prio_list);
	INIT_LIST_HEAD(&head->node_list);
#ifdef CONFIG_DEBUG_PI_LIST
	head->rawlock = lock;
	head->spinlock = NULL;
#endif
}

void mc_plist_node_init(struct mc_plist_node *node, int prio)
{
	node->prio = prio;
	mc_plist_head_init(&node->plist, NULL);
}

int mc_plist_head_empty(const struct mc_plist_head *head)
{
	return list_empty(&head->node_list);
}

int mc_plist_node_empty(const struct mc_plist_node *node)
{
	return mc_plist_head_empty(&node->plist);
}

struct mc_plist_node *mc_plist_first(const struct mc_plist_head *head)
{
	return list_entry(head->node_list.next,
			struct mc_plist_node, plist.node_list);
}

/**
 * plist_add - add @node to @head
 *
 * @node:	&struct plist_node pointer
 * @head:	&struct plist_head pointer
 */
void mc_plist_add(struct mc_plist_node *node, struct mc_plist_head *head)
{
	struct mc_plist_node *iter;

	mc_plist_check_head(head);
#if 0
	WARN_ON(!plist_node_empty(node));
#endif

	list_for_each_entry(iter, &head->prio_list, plist.prio_list) {
		if (node->prio < iter->prio)
			goto lt_prio;
		else if (node->prio == iter->prio) {
			iter = list_entry(iter->plist.prio_list.next,
					struct mc_plist_node, plist.prio_list);
			goto eq_prio;
		}
	}

lt_prio:
	list_add_tail(&node->plist.prio_list, &iter->plist.prio_list);
eq_prio:
	list_add_tail(&node->plist.node_list, &iter->plist.node_list);

	mc_plist_check_head(head);
}

/**
 * plist_del - Remove a @node from plist.
 *
 * @node:	&struct plist_node pointer - entry to be removed
 * @head:	&struct plist_head pointer - list head
 */
void mc_plist_del(struct mc_plist_node *node, struct mc_plist_head *head)
{
	mc_plist_check_head(head);

	if (!list_empty(&node->plist.prio_list)) {
		struct mc_plist_node *next = mc_plist_first(&node->plist);

		list_move_tail(&next->plist.prio_list, &node->plist.prio_list);
		list_del_init(&node->plist.prio_list);
	}

	list_del_init(&node->plist.node_list);

	mc_plist_check_head(head);
}
