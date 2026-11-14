#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (*count_fn)(void);
int main(void) {
    void *h = dlopen("/apps/libloader-lifecycle.so", RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) return EXIT_FAILURE;
    count_fn ctor = (count_fn)dlsym(h, "fixture_constructor_count");
    count_fn dtor = (count_fn)dlsym(h, "fixture_destructor_count");
    const char *err = dlerror();
    int before_ctor = ctor != NULL && err == NULL ? ctor() : -1;
    int before_dtor = dtor != NULL ? dtor() : -1;
    int close_rc = dlclose(h);
    int valid = before_ctor == 1 && before_dtor == 0 && close_rc == 0;
    printf("constructor=%d destructor_before=%d close=%d valid=%d\n", before_ctor, before_dtor, close_rc, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
