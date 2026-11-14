/* Nonshipped observer: all BFD objects/callbacks/providers are genuine. */
#include "/usr/include/bfd.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern long mcinspect_bfd_get_symtab_upper_bound_bridge(bfd *);
extern long eclair_bfd_get_symtab_upper_bound_bridge(bfd *);
extern long mcinspect_bfd_canonicalize_symtab_bridge(bfd *, asymbol **);
extern long eclair_bfd_canonicalize_symtab_bridge(bfd *, asymbol **);
int main(int argc, char **argv) {
    bfd *abfd = NULL;
    asymbol **reference = NULL, **mcinspect = NULL, **eclair = NULL;
    long expected_upper = -1, mc_upper = -1, ec_upper = -1;
    long reference_count = -1, mc_count = -1, ec_count = -1;
    int found = 0, result = 1, close_ok = 0;
    if (argc != 2) return 2;
    bfd_init();
    abfd = bfd_openr(argv[1], NULL);
    if (!abfd || !bfd_check_format(abfd, bfd_object)) goto done;
    expected_upper = bfd_get_symtab_upper_bound(abfd);
    mc_upper = mcinspect_bfd_get_symtab_upper_bound_bridge(abfd);
    ec_upper = eclair_bfd_get_symtab_upper_bound_bridge(abfd);
    if (expected_upper <= 0 || mc_upper != expected_upper || ec_upper != expected_upper) goto done;
    reference = malloc((size_t)expected_upper);
    mcinspect = malloc((size_t)expected_upper);
    eclair = malloc((size_t)expected_upper);
    if (!reference || !mcinspect || !eclair) goto done;
    reference_count = bfd_canonicalize_symtab(abfd, reference);
    mc_count = mcinspect_bfd_canonicalize_symtab_bridge(abfd, mcinspect);
    ec_count = eclair_bfd_canonicalize_symtab_bridge(abfd, eclair);
    if (reference_count <= 0 || reference_count != mc_count || reference_count != ec_count) goto done;
    for (long i = 0; i < reference_count; ++i) {
        const char *name = bfd_asymbol_name(reference[i]);
        if (!name || !mcinspect[i] || !eclair[i]) goto done;
        if (strcmp(name, bfd_asymbol_name(mcinspect[i])) || strcmp(name, bfd_asymbol_name(eclair[i]))) goto done;
        if (bfd_asymbol_value(reference[i]) != bfd_asymbol_value(mcinspect[i]) ||
            bfd_asymbol_value(reference[i]) != bfd_asymbol_value(eclair[i]) ||
            reference[i]->flags != mcinspect[i]->flags || reference[i]->flags != eclair[i]->flags) goto done;
        if (!strcmp(name, "m15_named_global")) {
            if (!(reference[i]->flags & BSF_GLOBAL) || bfd_is_und_section(reference[i]->section)) goto done;
            ++found;
        }
    }
    if (found != 1) goto done;
    result = 0;
done:
    free(eclair); free(mcinspect); free(reference);
    if (abfd) { close_ok = bfd_close(abfd); abfd = NULL; }
    if (!close_ok) result = 1;
    printf("{\"success\":%s,\"upper_bytes\":[%ld,%ld,%ld],\"symbol_counts\":[%ld,%ld,%ld],\"named_global_matches\":%d,\"close_ok\":%s,\"four_rust_bridges_compared\":4}\n",
        result == 0 ? "true" : "false", expected_upper,mc_upper,ec_upper,reference_count,mc_count,ec_count,found,close_ok ? "true" : "false");
    return result;
}
