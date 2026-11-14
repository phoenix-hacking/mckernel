/* NONSHIPPED functional BFD oracle diagnosis only. No Rust acceptance claim.
 * Compile only against the SAME pinned BFD SDK header/library as the failure.
 * Symbols remain BFD-owned; snapshots own only their copied names/metadata.
 */
#include "/usr/include/bfd.h"
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DECLARE(prefix) \
extern long original_##prefix##_bfd_get_symtab_upper_bound_bridge(bfd *); \
extern long original_##prefix##_bfd_canonicalize_symtab_bridge(bfd *, asymbol **)
DECLARE(mcinspect);
DECLARE(eclair);
typedef long (*upper_fn)(bfd *);
typedef long (*canon_fn)(bfd *, asymbol **);
struct symbol_snapshot {
    uintptr_t address;
    char *name;
    bfd_vma value;
    flagword flags;
};
static struct symbol_snapshot *snapshot(asymbol **table, long count) {
    assert(count > 0);
    struct symbol_snapshot *out = calloc((size_t)count, sizeof(*out));
    assert(out);
    for (long i = 0; i < count; ++i) {
        assert(table[i] && table[i]->name);
        size_t length = strlen(table[i]->name);
        out[i].name = malloc(length + 1);
        assert(out[i].name);
        memcpy(out[i].name, table[i]->name, length + 1);
        out[i].address = (uintptr_t)table[i];
        out[i].value = table[i]->value;
        out[i].flags = table[i]->flags;
    }
    return out;
}
static void release_snapshot(struct symbol_snapshot *symbols, long count) {
    for (long i = 0; i < count; ++i) free(symbols[i].name);
    free(symbols);
}
static void original_twice(const char *label, const char *path,
                           upper_fn upper, canon_fn canonicalize, int expect_symbols) {
    bfd *object = bfd_openr(path, NULL);
    assert(object && bfd_check_format(object, bfd_object));
    bfd_set_error(bfd_error_no_error); errno = EINTR;
    long size1 = upper(object); bfd_error_type upper_error1 = bfd_get_error();
    bfd_set_error(bfd_error_no_error); errno = EINTR;
    long size2 = upper(object); bfd_error_type upper_error2 = bfd_get_error();
    printf("UPPER %s %s %ld %ld %d %d\n", label, path, size1, size2,
           (int)upper_error1, (int)upper_error2);
    assert(size1 == size2 && upper_error1 == upper_error2 && size1 >= 0);
    assert(expect_symbols ? size1 > 0 : size1 == 0);
    if (size1 > 0) {
        asymbol **left = malloc((size_t)size1), **right = malloc((size_t)size1);
        assert(left && right);
        bfd_set_error(bfd_error_no_error); errno = EINTR;
        long count1 = canonicalize(object, left);
        bfd_error_type error1 = bfd_get_error(); int errno1 = errno;
        assert(count1 > 0 && (size_t)count1 < (size_t)size1 / sizeof(*left));
        /* Copy before the second call; do not read the first symbols after it. */
        struct symbol_snapshot *first = snapshot(left, count1);
        bfd_set_error(bfd_error_no_error); errno = EINTR;
        long count2 = canonicalize(object, right);
        bfd_error_type error2 = bfd_get_error(); int errno2 = errno;
        printf("CANON %s %s %ld %ld %d %d %d %d\n", label, path,
               count1, count2, (int)error1, (int)error2, errno1, errno2);
        assert(count1 == count2 && error1 == error2);
        struct symbol_snapshot *second = snapshot(right, count2);
        long changed = 0;
        for (long i = 0; i < count1; ++i) {
            int same_address = first[i].address == second[i].address;
            changed += !same_address;
            printf("SYMBOL %s %ld 0x%" PRIxPTR " 0x%" PRIxPTR " %s %s %" PRIuMAX " %" PRIuMAX " %" PRIuMAX " %" PRIuMAX "\n",
                   label, i, first[i].address, second[i].address,
                   first[i].name, second[i].name,
                   (uintmax_t)first[i].value, (uintmax_t)second[i].value,
                   (uintmax_t)first[i].flags, (uintmax_t)second[i].flags);
            assert(!strcmp(first[i].name, second[i].name));
            assert(first[i].value == second[i].value && first[i].flags == second[i].flags);
        }
        printf("POINTER_IDENTITY %s %ld %ld\n", label, count1, changed);
        release_snapshot(first, count1); release_snapshot(second, count2);
        free(left); free(right);
    }
    assert(bfd_close(object));
}
int main(int argc, char **argv) {
    assert(argc == 3); bfd_init();
#define CONTROL(prefix) \
    original_twice(#prefix, argv[1], original_##prefix##_bfd_get_symtab_upper_bound_bridge, \
                   original_##prefix##_bfd_canonicalize_symtab_bridge, 1); \
    original_twice(#prefix, argv[2], original_##prefix##_bfd_get_symtab_upper_bound_bridge, \
                   original_##prefix##_bfd_canonicalize_symtab_bridge, 0)
    CONTROL(mcinspect); CONTROL(eclair);
    puts("PASS ORIGINAL_C_TWICE_CONTROL_ONLY_NO_RUST_ABI_ACCEPTANCE");
    return 0;
}
