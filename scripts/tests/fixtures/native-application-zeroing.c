// SPDX-License-Identifier: GPL-2.0
// Exact extracted C zeroing bodies with bounded arena/list/NUMA providers.
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native-application-zeroing-c-layout.h"

#define PAGE_SHIFT 12
#define IHK_NUMA_ALL_PAGES 0
#define barrier() __asm__ __volatile__("" ::: "memory")
#define smp_store_release_ulong(p, v) __atomic_store_n((p), (v), __ATOMIC_RELEASE)
#define kprintf(...) ((void)0)
static int zero_at_free = 1;
static void *phys_to_virt(unsigned long address) { return (void *)address; }
static int ihk_mc_get_nr_numa_nodes(void) { return 0; }
static struct ihk_mc_numa_node *ihk_mc_get_numa_node_by_distance(int index)
{ (void)index; return NULL; }
static void init_llist_head(struct llist_head *head) { head->first = NULL; }
static struct llist_node *llist_del_first(struct llist_head *head)
{
    struct llist_node *node = head->first;
    if (node) head->first = node->next;
    return node;
}
static void llist_add(struct llist_node *node, struct llist_head *head)
{ node->next = head->first; head->first = node; }
static void ihk_atomic_sub(int value, ihk_atomic_t *counter)
{ counter->counter -= value; }
// Preserve the existing signed shift/unsigned-size comparison verbatim.
// All oracle request counts are nonnegative and bounded to 64 pages.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wsign-compare"
#include "native-application-zeroing-c-bodies.c"
#pragma GCC diagnostic pop

static unsigned long chain(struct llist_head *head)
{
    unsigned long value = 0;
    for (struct llist_node *p = head->first; p; p = p->next) {
        struct free_chunk *chunk = (void *)((char *)p - offsetof(struct free_chunk, list));
        value = value * 10 + chunk->node.__rb_parent_color;
    }
    return value;
}

int main(void)
{
    const int patterns[][5] = {{0}, {1,0}, {1,3,2,4,0}, {2,1,1,0}, {4,2,1,0}};
    const int requests[] = {0,1,2,4,5,64};
    printf("LAYOUT %zu %zu %zu %zu %zu %zu %zu %zu\n",
        sizeof(struct free_chunk), offsetof(struct free_chunk, list),
        sizeof(struct ihk_mc_numa_node), _Alignof(struct ihk_mc_numa_node),
        offsetof(struct ihk_mc_numa_node, zeroing_workers),
        offsetof(struct ihk_mc_numa_node, nr_to_zero_pages),
        offsetof(struct ihk_mc_numa_node, zeroed_list),
        offsetof(struct ihk_mc_numa_node, to_zero_list));
    for (unsigned p = 0; p < sizeof(patterns)/sizeof(patterns[0]); ++p) {
        for (unsigned r = 0; r < sizeof(requests)/sizeof(requests[0]); ++r) {
            struct ihk_mc_numa_node node = {0};
            void *storage[4] = {0};
            struct free_chunk *chunks[4] = {0};
            int count = 0;
            while (patterns[p][count]) {
                size_t size = (size_t)patterns[p][count] * 4096;
                assert(posix_memalign(&storage[count], 4096, size + 8192) == 0);
                memset(storage[count], 0xa5, size + 8192);
                chunks[count] = (void *)((char *)storage[count] + 4096);
                memset(chunks[count], 0, sizeof(*chunks[count]));
                chunks[count]->addr = (unsigned long)chunks[count];
                chunks[count]->size = size;
                chunks[count]->node.__rb_parent_color = count + 1;
                node.nr_to_zero_pages.counter += patterns[p][count];
                ++count;
            }
            for (int i = count - 1; i >= 0; --i) llist_add(&chunks[i]->list, &node.to_zero_list);
            int result = __ihk_numa_zero_free_pages(&node, requests[r]);
            unsigned cleared = 0;
            for (int i = 0; i < count; ++i) {
                size_t size = (size_t)patterns[p][i] * 4096;
                unsigned char *bytes = storage[i];
                for (size_t n = 0; n < 4096; ++n) {
                    assert(bytes[n] == 0xa5);
                    assert(bytes[4096 + size + n] == 0xa5);
                }
                unsigned char value = bytes[4096 + sizeof(struct free_chunk)];
                assert(value == 0 || value == 0xa5);
                for (size_t n = sizeof(struct free_chunk); n < size; ++n)
                    assert(bytes[4096 + n] == value);
                assert(chunks[i]->addr == (unsigned long)chunks[i]);
                assert(chunks[i]->size == size);
                assert(chunks[i]->node.__rb_parent_color == (unsigned long)i + 1);
                assert(chunks[i]->node.rb_left == NULL && chunks[i]->node.rb_right == NULL);
                if (value == 0) cleared |= 1u << i;
            }
            printf("ZERO %u %d %d %d %lu %lu %u\n", p, requests[r], result,
                node.nr_to_zero_pages.counter, chain(&node.to_zero_list), chain(&node.zeroed_list), cleared);
            for (int i = 0; i < count; ++i) free(storage[i]);
        }
    }
    for (unsigned i = 0; i < 6; ++i) {
        struct ikc_scd_packet packet;
        unsigned long number = i == 5 ? 0x12345678UL : 279;
        memset(&packet, 0xa5, sizeof(packet));
        __ihk_numa_zero_request_packet_fill(&packet,
            0xfffffffffe910040UL + i * 256, i, 307 + i, number);
        printf("PACKET ");
        for (unsigned n = 0; n < sizeof(packet); ++n) printf("%02x", ((unsigned char *)&packet)[n]);
        printf("\n");
    }
    return 0;
}
