/*
  Red Black Trees
  (C) 1999  Andrea Arcangeli <andrea@suse.de>
  (C) 2002  David Woodhouse <dwmw2@infradead.org>
  (C) 2012  Michel Lespinasse <walken@google.com>

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

  linux/include/linux/rbtree_augmented.h
*/

#ifndef _LINUX_RBTREE_AUGMENTED_H
#define _LINUX_RBTREE_AUGMENTED_H

#include <rbtree.h>

/*
 * Please note - only struct rb_augment_callbacks and the prototypes for
 * rb_insert_augmented() and rb_erase_augmented() are intended to be public.
 * The rest are implementation details you are not expected to depend on.
 *
 * See Documentation/rbtree.txt for documentation and samples.
 */

struct rb_augment_callbacks {
	void (*propagate)(struct rb_node *node, struct rb_node *stop);
	void (*copy)(struct rb_node *old, struct rb_node *new);
	void (*rotate)(struct rb_node *old, struct rb_node *new);
};

extern void __rb_insert_augmented(struct rb_node *node, struct rb_root *root,
	void (*augment_rotate)(struct rb_node *old, struct rb_node *new));
void rb_insert_augmented(struct rb_node *node, struct rb_root *root,
			 const struct rb_augment_callbacks *augment);

#define	RB_RED		0
#define	RB_BLACK	1

struct rb_node *__rb_parent(unsigned long pc);
unsigned long __rb_color(unsigned long pc);
int __rb_is_black(unsigned long pc);
int __rb_is_red(unsigned long pc);
unsigned long rb_color(const struct rb_node *rb);
int rb_is_red(const struct rb_node *rb);
int rb_is_black(const struct rb_node *rb);
void rb_set_parent(struct rb_node *rb, struct rb_node *p);
void rb_set_parent_color(struct rb_node *rb, struct rb_node *p, int color);
void __rb_change_child(struct rb_node *old, struct rb_node *new,
		       struct rb_node *parent, struct rb_root *root);

extern void __rb_erase_color(struct rb_node *parent, struct rb_root *root,
	void (*augment_rotate)(struct rb_node *old, struct rb_node *new));
struct rb_node *__rb_erase_augmented(struct rb_node *node, struct rb_root *root,
				     const struct rb_augment_callbacks *augment);
void rb_erase_augmented(struct rb_node *node, struct rb_root *root,
			const struct rb_augment_callbacks *augment);

#endif	/* _LINUX_RBTREE_AUGMENTED_H */
