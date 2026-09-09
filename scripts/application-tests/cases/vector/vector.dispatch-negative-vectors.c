#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct features { uint32_t max_basic; uint32_t leaf1_ecx, leaf1_edx, leaf7_ebx; uint64_t xcr0, leafd_mask; };
static int supports(const struct features *f, uint64_t required_cpuid, uint64_t required_xcr0, uint32_t max_leaf) {
    return f->max_basic >= max_leaf && (f->leaf1_ecx & (uint32_t)required_cpuid) == (uint32_t)required_cpuid && (f->xcr0 & required_xcr0) == required_xcr0;
}
int main(void) {
    const struct features baseline = {0xD, 0x1C000000u, 0x07000000u, 0x20u, 0x6u, 0x3u};
    const struct features no_avx = {0xD, 0x14000000u, 0x07000000u, 0x20u, 0x6u, 0x3u};
    const struct features no_osxsave = {0xD, 0x04000000u, 0x07000000u, 0x20u, 0x6u, 0x3u};
    const struct features no_sse_xcr = {0xD, 0x1C000000u, 0x07000000u, 0x20u, 0x4u, 0x3u};
    int accepted = supports(&baseline, 0x1C000000u, 0x6u, 1), rejected = !supports(&no_avx, 0x1C000000u, 0x6u, 1) && !supports(&no_osxsave, 0x1C000000u, 0x6u, 1) && !supports(&no_sse_xcr, 0x1C000000u, 0x6u, 1);
    int valid = accepted && rejected;
    printf("accepted=%d rejected=%d optional_instructions=0 valid=%d\n", accepted, rejected, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
