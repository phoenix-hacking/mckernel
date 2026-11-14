#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct xsave_area { unsigned char bytes[16384] __attribute__((aligned(64))); };
int main(void) {
    struct xsave_area area = {{0}}; uint32_t eax = 0x3u, edx = 0u;
    __asm__ volatile("xsave64 %0" : "=m"(area) : "a"(eax), "d"(edx) : "memory");
    uint64_t xstate_bv = *(const uint64_t *)(area.bytes + 512);
    int aligned = ((uintptr_t)area.bytes & 63u) == 0;
    int mask_ok = (xstate_bv & ~UINT64_C(0x3)) == 0;
    int valid = aligned && mask_ok;
    printf("aligned=%d requested_mask=3 xstate_bv=%llu xcomp_bv=0 mask_ok=%d valid=%d\n", aligned, (unsigned long long)xstate_bv, mask_ok, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
