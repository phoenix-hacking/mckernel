#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    void *h = dlopen("/apps/libloader-fixture.so", RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) return EXIT_FAILURE;
    (void)dlerror();
    void *missing = dlsym(h, "fixture_symbol_that_does_not_exist");
    const char *missing_error = dlerror();
    (void)dlerror();
    void *present = dlsym(h, "fixture_add");
    const char *present_error = dlerror();
    int valid = missing == NULL && missing_error != NULL && *missing_error != '\0' && present != NULL && present_error == NULL && dlclose(h) == 0;
    printf("missing_null=%d error_nonempty=%d present=%d present_error=%d valid=%d\n", missing == NULL, missing_error != NULL && *missing_error != '\0', present != NULL, present_error != NULL, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
