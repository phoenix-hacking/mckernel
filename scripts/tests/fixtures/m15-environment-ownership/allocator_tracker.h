/* Reused reviewed allocator tracker; fixture-only, genuine libc delegation. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ihk/ihklib_private.h>
/* Exact private function signature in the retained ihklib.c definition.
 * ihklib_private.h defines its bounds but does not declare this private root. */
extern int parse_env(const char *, int, char ***, char ***);
extern void *__real_calloc(size_t, size_t);
extern char *__real_strndup(const char *, size_t);
extern char *__real_strdup(const char *);
extern void __real_free(void *);
static void *owned[32];
static int active, attempts, fail_at, live, checks, failures;
static int fail(void) { if (!active) return 0; ++attempts; if (attempts != fail_at) return 0; errno=ENOMEM; return 1; }
static void *record(void *p) { if (active && p) { for (int i=0;i<32;i++) if (!owned[i]) { owned[i]=p; ++live; return p; } abort(); } return p; }
void *__wrap_calloc(size_t n,size_t s) { return fail()?NULL:record(__real_calloc(n,s)); }
char *__wrap_strndup(const char *p,size_t n) { return fail()?NULL:record(__real_strndup(p,n)); }
char *__wrap_strdup(const char *p) { return fail()?NULL:record(__real_strdup(p)); }
void __wrap_free(void *p) {
 if (active && p) { int found=0; for (int i=0;i<32;i++) if (owned[i]==p) { owned[i]=NULL; --live; found=1; break; } if (!found) abort(); }
 __real_free(p);
#ifdef TRACKER_POISON_FREE_ERRNO
 errno=EIO; /* Callback-only deterministic cleanup effect; never reread freed p. */
#endif
}
static void reset(int ordinal) { if(live) abort(); active=1; attempts=0; fail_at=ordinal; }
static int discard(void) { int reclaimed=0; active=0; for(int i=0;i<32;i++) if(owned[i]) { __real_free(owned[i]); owned[i]=NULL; ++reclaimed; } live=0; return reclaimed; }
