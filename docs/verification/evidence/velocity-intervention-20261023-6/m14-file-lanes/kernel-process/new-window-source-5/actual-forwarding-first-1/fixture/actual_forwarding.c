/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual original/fixed provider bodies; controlled allocation/free effects only.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct vm_range;
struct mckfd;
#define IHK_MC_AP_NOWAIT 2UL
struct event {
    int kind, size, line;
    unsigned long flags;
    void *pointer;
    const char *file;
};
static struct event observed;
static int calls;
static void *next_result;

void *fixture_tracked_alloc(int size, unsigned long flags, char *file, int line)
{
    observed = (struct event){ .kind=1, .size=size, .line=line, .flags=flags,
                              .pointer=next_result, .file=file };
    ++calls;
    return next_result;
}
void fixture_tracked_free(void *pointer, char *file, int line)
{
    observed = (struct event){ .kind=2, .line=line, .pointer=pointer, .file=file };
    ++calls;
}
void *kmalloc_tracked(int size, unsigned long flags, char *file, int line)
{
    return fixture_tracked_alloc(size, flags, file, line);
}
void kfree_tracked(void *pointer, char *file, int line)
{
    fixture_tracked_free(pointer, file, line);
}
#include "exact_metadata.ACTUAL-C.inc"
#include "all_original_bodies.ACTUAL-C.inc"

extern void *process_alloc_bridge(unsigned long, unsigned long);
extern struct vm_range *process_add_range_alloc_bridge(unsigned long);
extern void process_mckfd_free_bridge(struct mckfd *);
extern void process_policy_free_bridge(void *);
extern void process_optional_free_bridge(void *);
extern void process_free_vm_bridge(void *);
extern void process_range_kfree_bridge(struct vm_range *);
extern void process_add_range_free_bridge(struct vm_range *);

static void clear(void) { calls=0; memset(&observed, 0, sizeof(observed)); }
static void compare(struct event expected, int line)
{
    assert(calls == 1);
    assert(observed.kind == expected.kind);
    assert(observed.size == expected.size);
    assert(observed.flags == expected.flags);
    assert(observed.pointer == expected.pointer);
    assert(observed.line == expected.line && observed.line == line);
    assert(strcmp(observed.file, expected.file) == 0);
    assert(strcmp(observed.file, process_tracked_allocator_source_file) == 0);
}

int main(void)
{
    const unsigned long sizes[] = {0, 1, INT_MAX, 0x80000000UL, 0xffffffffUL,
                                   0x100000001UL, ULONG_MAX};
    const unsigned long flags[] = {0, IHK_MC_AP_NOWAIT, 1UL<<63, ULONG_MAX};
    int comparisons=0;
    for (int result=0; result<2; ++result) {
        next_result = result ? (void *)(uintptr_t)0x12340000 : NULL;
        for (size_t i=0; i<sizeof(sizes)/sizeof(sizes[0]); ++i) {
            for (size_t j=0; j<sizeof(flags)/sizeof(flags[0]); ++j) {
                clear();
                void *expected_result = reference_process_alloc_bridge(sizes[i], flags[j]);
                assert(calls == 1);
                struct event expected=observed;
                clear();
                assert(process_alloc_bridge(sizes[i], flags[j]) == expected_result);
                compare(expected, process_alloc_bridge_source_line);
                assert(observed.size == (int)sizes[i] && observed.flags == flags[j]);
                ++comparisons;
            }
            clear();
            struct vm_range *expected_result=reference_process_add_range_alloc_bridge(sizes[i]);
            assert(calls == 1);
            struct event expected=observed;
            clear();
            assert(process_add_range_alloc_bridge(sizes[i]) == expected_result);
            compare(expected, process_add_range_alloc_bridge_source_line);
            assert(observed.size == (int)sizes[i] && observed.flags == IHK_MC_AP_NOWAIT);
            ++comparisons;
        }
    }
    for (int pointer=0; pointer<2; ++pointer) {
        void *value=pointer ? (void *)(uintptr_t)0x12340000 : NULL;
#define CHECK_FREE(name, cast) do { \
        clear(); reference_##name((cast)value); assert(calls == 1); \
        struct event expected=observed; clear(); name((cast)value); \
        compare(expected, name##_source_line); \
        assert(observed.kind == 2 && observed.pointer == value); ++comparisons; \
    } while (0)
        CHECK_FREE(process_mckfd_free_bridge, struct mckfd *);
        CHECK_FREE(process_policy_free_bridge, void *);
        CHECK_FREE(process_optional_free_bridge, void *);
        CHECK_FREE(process_free_vm_bridge, void *);
        CHECK_FREE(process_range_kfree_bridge, struct vm_range *);
        CHECK_FREE(process_add_range_free_bridge, struct vm_range *);
#undef CHECK_FREE
    }
    assert(comparisons == 82);
    printf("PASS actual-original-C/Rust tracked forwarding: 82 comparisons, eight providers, narrowing/flags/null/free/file/line\n");
    return 0;
}
