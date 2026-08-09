#ifndef _LINUX_LIST_H
#define _LINUX_LIST_H

#ifndef offsetof
#define offsetof __builtin_offsetof
#endif

struct list_head {
	struct list_head *next, *prev;
};

#define LIST_POISON1 ((void *)0x00100129)
#define LIST_POISON2 ((void *)0x00200229)

void INIT_LIST_HEAD(struct list_head *list);
void __list_add(struct list_head *new, struct list_head *prev,
		struct list_head *next);
void list_add(struct list_head *new, struct list_head *head);
void list_add_tail(struct list_head *new, struct list_head *head);
void __list_del(struct list_head *prev, struct list_head *next);
void __list_del_entry(struct list_head *entry);
void list_del(struct list_head *entry);
void list_replace(struct list_head *old, struct list_head *new);
void list_replace_init(struct list_head *old, struct list_head *new);
void list_del_init(struct list_head *entry);
void list_move(struct list_head *list, struct list_head *head);
void list_move_tail(struct list_head *list, struct list_head *head);
int list_is_last(const struct list_head *list, const struct list_head *head);
int list_empty(const struct list_head *head);
int list_empty_careful(const struct list_head *head);
void list_rotate_left(struct list_head *head);
int list_is_singular(const struct list_head *head);
void __list_cut_position(struct list_head *list, struct list_head *head,
		struct list_head *entry);
void list_cut_position(struct list_head *list, struct list_head *head,
		struct list_head *entry);
void __list_splice(const struct list_head *list, struct list_head *prev,
		struct list_head *next);
void list_splice(const struct list_head *list, struct list_head *head);
void list_splice_tail(struct list_head *list, struct list_head *head);
void list_splice_init(struct list_head *list, struct list_head *head);
void list_splice_tail_init(struct list_head *list, struct list_head *head);

#endif
