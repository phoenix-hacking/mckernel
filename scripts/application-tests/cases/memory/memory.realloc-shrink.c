#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const size_t old_size = 2048;
    const size_t new_size = 64;

    unsigned char *ptr = malloc(old_size);
    if (!ptr) {
        printf("realloc-shrink status=ALLOC_FAIL errno=%d\n", errno);
        return 1;
    }

    for (size_t i = 0; i < old_size; i++) {
        ptr[i] = (unsigned char)(0x40 + (i & 0x3F));
    }

    unsigned char *shrunk = realloc(ptr, new_size);
    if (!shrunk) {
        printf("realloc-shrink status=REALLOC_FAIL errno=%d\n", errno);
        free(ptr);
        return 1;
    }

    int unchanged = 1;
    for (size_t i = 0; i < new_size; i++) {
        if (shrunk[i] != (unsigned char)(0x40 + (i & 0x3F))) {
            unchanged = 0;
            break;
        }
    }

    printf("realloc-shrink status=%s\n", unchanged ? "PASS" : "FAIL");
    free(shrunk);
    return unchanged ? 0 : 1;
}
