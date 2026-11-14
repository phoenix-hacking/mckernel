#define _GNU_SOURCE

#include <stdint.h>

int main(void) {
    volatile uint32_t *unmapped = (volatile uint32_t *)(uintptr_t)1;
    *unmapped = 0xdeadbeefU;
    return 0;
}
