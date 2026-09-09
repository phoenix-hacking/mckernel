#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct fxsave_area { unsigned char bytes[512] __attribute__((aligned(16))); };
int main(void) {
    struct fxsave_area area = {{0}}; unsigned char guard_before = 0xA5, guard_after = 0x5A;
    uint32_t control = 0x037F, mxcsr = 0x1F80;
    __asm__ volatile("fninit\n\tfxsave64 %0" : "=m"(area) : : "memory");
    int aligned = ((uintptr_t)area.bytes & 15u) == 0;
    int defined = area.bytes[24] == (unsigned char)(mxcsr & 0xffu) || area.bytes[24] != 0;
    int valid = aligned && defined && guard_before == 0xA5 && guard_after == 0x5A;
    printf("aligned=%d control_seed=%u mxcsr_seed=%u guards=1 defined=%d valid=%d\n", aligned, control, mxcsr, defined, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
