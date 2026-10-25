/* NONSHIPPED configure/test orchestration, never linked into production. */
#include "/usr/include/bfd.h"
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#ifdef DEBUG_BFD_SEND
#error DEBUG_BFD_SEND is outside the qualified accessor contract
#endif
#if !defined(__x86_64__) || !defined(__linux__)
#error qualified platform is x86_64 Linux
#endif
_Static_assert(CHAR_BIT == 8 && sizeof(long) == 8 && sizeof(void *) == 8, "LP64 ABI");
typedef long (*upper_type)(bfd *);
typedef long (*canonicalize_type)(bfd *, asymbol **);
_Static_assert(_Generic(((bfd_target *)0)->_bfd_get_symtab_upper_bound,
                       upper_type: 1, default: 0), "upper callback ABI");
_Static_assert(_Generic(((bfd_target *)0)->_bfd_canonicalize_symtab,
                       canonicalize_type: 1, default: 0), "canonicalize callback ABI");
_Static_assert(sizeof(upper_type) == 8 && sizeof(canonicalize_type) == 8, "function pointer ABI");
_Static_assert(_Alignof(upper_type) == 8 && _Alignof(canonicalize_type) == 8, "callback alignment");
_Static_assert(offsetof(bfd, xvec) % 8 == 0, "xvec alignment");
_Static_assert(offsetof(bfd_target, _bfd_get_symtab_upper_bound) % 8 == 0, "upper alignment");
_Static_assert(offsetof(bfd_target, _bfd_canonicalize_symtab) % 8 == 0, "canonicalize alignment");
/* Preprocess these two separately to retain the actual BFD_SEND expansion. */
long witness_upper(bfd *b) { return bfd_get_symtab_upper_bound(b); }
long witness_canonicalize(bfd *b, asymbol **s) { return bfd_canonicalize_symtab(b, s); }
int main(void) {
    printf("// Generated from selected pinned BFD header; not a portable BFD layout.\n");
    printf("pub const BFD_XVEC_OFFSET: usize = %zu;\n", offsetof(bfd, xvec));
    printf("pub const BFD_UPPER_OFFSET: usize = %zu;\n", offsetof(bfd_target, _bfd_get_symtab_upper_bound));
    printf("pub const BFD_CANONICALIZE_OFFSET: usize = %zu;\n", offsetof(bfd_target, _bfd_canonicalize_symtab));
    printf("// sizeof(bfd)=%zu align=%zu; sizeof(bfd_target)=%zu align=%zu\n",
           sizeof(bfd), _Alignof(bfd), sizeof(bfd_target), _Alignof(bfd_target));
    return 0;
}
