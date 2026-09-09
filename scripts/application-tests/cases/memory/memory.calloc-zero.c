#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int verify_zero_block(const unsigned char *block, size_t size) {
    for (size_t i = 0; i < size; i++) {
        if (block[i] != 0) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    const size_t requested_bytes[] = {1, 4095, 4096, 4097, 65553, 1048576};
    const int cases = 6;
    int failed = 0;

    for (int i = 0; i < cases; i++) {
        const size_t bytes = requested_bytes[i];
        unsigned char *ptr = calloc(1, bytes);
        if (!ptr) {
            printf("calloc-zero size=%zu errno=%d status=FAIL\n", bytes, errno);
            failed = 1;
            continue;
        }
        int ok = verify_zero_block(ptr, bytes);
        printf("calloc-zero size=%zu status=%s\n", bytes, ok ? "PASS" : "FAIL");
        free(ptr);
        if (!ok) {
            failed = 1;
        }
    }

    return failed ? 1 : 0;
}
