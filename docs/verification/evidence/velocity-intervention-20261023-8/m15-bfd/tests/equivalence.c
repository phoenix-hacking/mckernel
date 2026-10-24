/* NONSHIPPED functional ABI/equivalence harness. No guest or kernel access. */
#include "/usr/include/bfd.h"
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DECLARE(prefix) \
extern long prefix##_bfd_get_symtab_upper_bound_bridge(bfd *); \
extern long prefix##_bfd_canonicalize_symtab_bridge(bfd *, asymbol **)
DECLARE(mcinspect);
DECLARE(eclair);
DECLARE(original_mcinspect);
DECLARE(original_eclair);
typedef long (*upper_fn)(bfd *);
typedef long (*canon_fn)(bfd *, asymbol **);
static bfd *expected_bfd;
static asymbol **expected_table;
static asymbol fake_symbol;
static long callback_result;
static int calls, change_error;
static long upper_callback(bfd *b) {
    assert(b == expected_bfd); ++calls;
    if (change_error) { bfd_set_error(bfd_error_invalid_operation); errno = EIO; }
    return callback_result;
}
static long upper_callback_alt(bfd *b) {
    assert(b == expected_bfd); ++calls; return 43;
}
static long canonicalize_callback(bfd *b, asymbol **s) {
    assert(b == expected_bfd && s == expected_table); ++calls;
    if (s) s[0] = &fake_symbol;
    if (change_error) { bfd_set_error(bfd_error_invalid_operation); errno = EIO; }
    return callback_result;
}
static void reset(void) {
    calls = 0;
    bfd_set_error(bfd_error_no_symbols);
    errno = EINTR;
}
static void fake_equivalence(upper_fn original_upper, upper_fn rust_upper,
                             canon_fn original_canon, canon_fn rust_canon) {
    bfd_target target = {0};
    bfd fake = {0};
    asymbol *table[2] = {NULL, NULL};
    long results[] = {LONG_MIN, -127, -1, 0, 1, 127, LONG_MAX};
    target._bfd_get_symtab_upper_bound = upper_callback;
    target._bfd_canonicalize_symtab = canonicalize_callback;
    fake.xvec = &target;
    expected_bfd = &fake;
    for (size_t i = 0; i < sizeof(results)/sizeof(results[0]); ++i)
      for (change_error = 0; change_error <= 1; ++change_error) {
        callback_result = results[i];
        reset(); long a = original_upper(&fake);
        assert(calls == 1); bfd_error_type e = bfd_get_error(); int saved_errno = errno;
        reset(); long b = rust_upper(&fake);
        assert(a == b && b == callback_result && calls == 1);
        assert(e == bfd_get_error() && saved_errno == errno);
        for (int null_table = 0; null_table <= 1; ++null_table) {
          expected_table = null_table ? NULL : table;
          reset(); table[0] = NULL;
          a = original_canon(&fake, expected_table);
          assert(calls == 1 && (null_table || table[0] == &fake_symbol));
          e = bfd_get_error(); saved_errno = errno;
          reset(); table[0] = NULL;
          b = rust_canon(&fake, expected_table);
          assert(a == b && b == callback_result && calls == 1);
          assert(null_table || table[0] == &fake_symbol);
          assert(e == bfd_get_error() && saved_errno == errno);
        }
      }
    /* A different live target/callback verifies every call rereads xvec. */
    bfd_target target2 = target;
    target2._bfd_get_symtab_upper_bound = upper_callback_alt;
    fake.xvec = &target2;
    change_error = 0; callback_result = 42; reset();
    assert(rust_upper(&fake) == 43 && calls == 1);
}
static void real_equivalence(const char *path, upper_fn original_upper, upper_fn rust_upper,
                             canon_fn original_canon, canon_fn rust_canon, int expect_symbols) {
    bfd *b = bfd_openr(path, NULL);
    assert(b && bfd_check_format(b, bfd_object));
    bfd_set_error(bfd_error_no_error);
    long a = original_upper(b); bfd_error_type e = bfd_get_error();
    bfd_set_error(bfd_error_no_error);
    long r = rust_upper(b);
    assert(a == r && e == bfd_get_error() && a >= 0);
    if (expect_symbols) assert(a > 0);
    else assert(a == 0);
    if (a > 0) {
      asymbol **left = malloc((size_t)a), **right = malloc((size_t)a);
      assert(left && right);
      bfd_set_error(bfd_error_no_error); long n = original_canon(b, left); e = bfd_get_error();
      bfd_set_error(bfd_error_no_error); long m = rust_canon(b, right);
      assert(n == m && n > 0 && e == bfd_get_error());
      for (long i = 0; i < n; ++i) {
        assert(left[i] == right[i]);
        assert(!strcmp(left[i]->name, right[i]->name));
        assert(left[i]->value == right[i]->value && left[i]->flags == right[i]->flags);
      }
      free(left); free(right);
    }
    assert(bfd_close(b));
}
int main(int argc, char **argv) {
    assert(argc == 3); bfd_init();
#define RUN(prefix) \
    fake_equivalence(original_##prefix##_bfd_get_symtab_upper_bound_bridge, \
                     prefix##_bfd_get_symtab_upper_bound_bridge, \
                     original_##prefix##_bfd_canonicalize_symtab_bridge, \
                     prefix##_bfd_canonicalize_symtab_bridge); \
    real_equivalence(argv[1], original_##prefix##_bfd_get_symtab_upper_bound_bridge, \
                     prefix##_bfd_get_symtab_upper_bound_bridge, \
                     original_##prefix##_bfd_canonicalize_symtab_bridge, \
                     prefix##_bfd_canonicalize_symtab_bridge, 1); \
    real_equivalence(argv[2], original_##prefix##_bfd_get_symtab_upper_bound_bridge, \
                     prefix##_bfd_get_symtab_upper_bound_bridge, \
                     original_##prefix##_bfd_canonicalize_symtab_bridge, \
                     prefix##_bfd_canonicalize_symtab_bridge, 0)
    RUN(mcinspect); RUN(eclair);
    puts("PASS four original-C/Rust accessor ABI, exact callback arguments, long extrema, errors, symbol/no-symbol objects, ownership/lifetime");
    return 0;
}
