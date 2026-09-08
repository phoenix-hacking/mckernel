/* SPDX-License-Identifier: GPL-2.0-only */
/* Unchanged legacy tree bodies, with Linux effects replaced only in this
 * userspace reference. The separate Rust guest exercises real Linux sysfs. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

struct list_head { struct list_head *next, *prev; };
#define INIT_LIST_HEAD(p) ((p)->next = (p), (p)->prev = (p))
#define list_entry(p, t, member) ((t *)((char *)(p) - offsetof(t, member)))
#define list_first_entry(p, t, member) list_entry((p)->next, t, member)
#define list_for_each_entry(p, h, member) \
    for ((p) = list_entry((h)->next, __typeof__(*(p)), member); \
         &(p)->member != (h); (p) = list_entry((p)->member.next, __typeof__(*(p)), member))
static int list_empty(struct list_head *head) { return head->next == head; }
static void list_add(struct list_head *node, struct list_head *head) {
    node->next = head->next; node->prev = head;
    head->next->prev = node; head->next = node;
}
static void list_del(struct list_head *node) {
    node->next->prev = node->prev; node->prev->next = node->next;
}
struct kobject { unsigned unused; };
struct attribute { const char *name; mode_t mode; };
struct semaphore { unsigned unused; };
struct sysfsm_ops { void (*release)(struct sysfsm_ops *, void *); };
enum { SNT_DIR, SNT_FILE, SNT_LINK };
struct sysfsm_node {
    int type; char *name; struct sysfsm_node *parent; struct sysfsm_data *sdp;
    struct list_head chain, children; struct kobject kobj; struct attribute attr;
    struct sysfsm_ops *server_ops; long client_ops, client_instance;
};
struct sysfsm_data {
    struct sysfsm_node *sysfs_root; struct kobject *sysfs_kobj;
    struct semaphore sysfs_tree_sem;
};
static int the_ktype;
#define GFP_KERNEL 0
#define SYSFS_UNLINK_KEEP_ANCESTOR 1
#define BUG_ON(test) assert(!(test))
#define BUG() abort()
#define dprintk(...) ((void)0)
#define eprintk(...) ((void)0)
#define ERR_PTR(error) ((void *)(intptr_t)(error))
#define PTR_ERR(pointer) ((int)(intptr_t)(pointer))
#define IS_ERR(pointer) ((uintptr_t)(pointer) >= (uintptr_t)-4095)
#define kzalloc(size, flags) calloc(1, size)
#define kstrdup(name, flags) strdup(name)
#define kfree(pointer) free(pointer)
static int down_interruptible(struct semaphore *sem) { return 0; }
static void up(struct semaphore *sem) {}
static int kobject_init_and_add(struct kobject *object, int *type, struct kobject *parent, const char *format, ...) { return 0; }
static void kobject_del(struct kobject *object) {}
static int sysfs_create_file(struct kobject *parent, struct attribute *attribute) { return 0; }
static void sysfs_remove_file(struct kobject *parent, struct attribute *attribute) {}
static int sysfs_create_link(struct kobject *parent, struct kobject *target, const char *name) { return 0; }
static void sysfs_remove_link(struct kobject *parent, const char *name) {}

/* Avoid libc's unrelated remove declaration without changing a legacy body. */
#define remove legacy_remove
#include "native-sysfs-tree-reference-bodies.h"
#undef remove

static size_t count_nodes(struct sysfsm_node *node) {
    size_t count = 1;
    if (node->type == SNT_DIR) {
        struct sysfsm_node *child;
        list_for_each_entry(child, &node->children, chain) count += count_nodes(child);
    }
    return count;
}
static void free_tree(struct sysfsm_node *node) {
    if (node->type == SNT_DIR) {
        while (!list_empty(&node->children)) {
            struct sysfsm_node *child = list_first_entry(&node->children, struct sysfsm_node, chain);
            list_del(&child->chain); free_tree(child);
        }
    }
    free(node->name); free(node);
}

int main(int argc, char **argv) {
    assert(argc == 2);
    FILE *cases = fopen(argv[1], "r"); assert(cases);
    struct sysfsm_data data = {0}; struct kobject parent = {0};
    struct sysfsm_node *root = calloc(1, sizeof(*root)); assert(root);
    root->type = SNT_DIR; root->name = strdup("(the_root)"); assert(root->name);
    root->parent = root; root->sdp = &data;
    INIT_LIST_HEAD(&root->chain); INIT_LIST_HEAD(&root->children);
    data.sysfs_root = root; data.sysfs_kobj = &parent;
    assert(!IS_ERR(mkdir_i(root, "sys")));
    char *line = NULL; size_t capacity = 0, index = 0; ssize_t bytes;
    while ((bytes = getline(&line, &capacity, cases)) >= 0) {
        if (bytes && line[bytes - 1] == '\n') line[--bytes] = 0;
        if (!bytes) continue;
        char *cursor = line, *operation = strsep(&cursor, "|"), *path = strsep(&cursor, "|"), *argument = strsep(&cursor, "|");
        assert(operation && path && argument && !cursor);
        struct sysfsm_node *result = NULL; int error = 0;
        switch (*operation) {
        case 'K': result = sysfsm_lookup(&data, path); break;
        case 'D': result = sysfsm_mkdir(&data, path); break;
        case 'F': result = sysfsm_create(&data, path, 0444, NULL, 0, 0); break;
        case 'L':
            result = sysfsm_lookup(&data, argument);
            if (!IS_ERR(result)) result = sysfsm_symlink(&data, result, path);
            break;
        case 'U': error = sysfsm_unlink(&data, path, atoi(argument)); break;
        default: abort();
        }
        if (IS_ERR(result)) error = PTR_ERR(result);
        printf("%zu %d %zu\n", index++, error, count_nodes(root));
    }
    assert(!ferror(cases)); fclose(cases); free(line); free_tree(root);
    return 0;
}
