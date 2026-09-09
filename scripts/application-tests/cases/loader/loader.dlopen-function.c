#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    void *handle = dlopen("/apps/libloader-fixture.so", RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) return EXIT_FAILURE;
    int (*fixture_add)(int, int) = (int (*)(int, int))dlsym(handle, "fixture_add");
    const char *error = dlerror();
    int result = fixture_add != NULL && error == NULL ? fixture_add(19, 23) : -1;
    int close_rc = dlclose(handle);
    int valid = result == 42 && close_rc == 0;
    printf("symbol=%d result=%d close=%d valid=%d\n", fixture_add != NULL && error == NULL, result, close_rc, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
