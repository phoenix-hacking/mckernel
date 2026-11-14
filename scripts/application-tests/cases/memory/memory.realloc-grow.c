#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const size_t old_size = 32;
    const size_t new_size = 2048;

    unsigned char *ptr = malloc(old_size);
    if (!ptr) {
        printf("realloc-grow status=ALLOC_FAIL errno=%d\n", errno);
        return 1;
    }

    for (size_t i = 0; i < old_size; i++) {
        ptr[i] = (unsigned char)(0xA5 + (i & 0x1F));
    }

    unsigned char *grown = realloc(ptr, new_size);
    if (!grown) {
        printf("realloc-grow status=REALLOC_FAIL errno=%d\n", errno);
        free(ptr);
        return 1;
    }

    int unchanged = 1;
    for (size_t i = 0; i < old_size; i++) {
        if (grown[i] != (unsigned char)(0xA5 + (i & 0x1F))) {
            unchanged = 0;
            break;
        }
    }

    printf("realloc-grow status=%s\n", unchanged ? "PASS" : "FAIL");
    free(grown);
    return unchanged ? 0 : 1;
}
