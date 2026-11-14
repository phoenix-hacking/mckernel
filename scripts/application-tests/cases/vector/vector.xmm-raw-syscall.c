#include <stdio.h>
#include <stdint.h>
#include <sys/syscall.h>

struct xmm_window {
    uint8_t before[16][16];
    uint8_t after_getpid[16][16];
    uint8_t after_gettid[16][16];
    uint8_t after_write[16][16];
    uint8_t after_yield[16][16];
};

struct xmm_case_result {
    struct xmm_window window;
    long getpid_ret;
    long gettid_ret;
    long write_ret;
    long yield_ret;
    char write_byte;
};

static void fill_seed(uint8_t out[16][16]) {
    for (uint32_t reg = 0; reg < 16; ++reg) {
        for (uint32_t b = 0; b < 16; ++b) {
            out[reg][b] = (uint8_t)((reg * 0x13u + b * 0x1Fu + 0x5Au) & 0xFFu);
        }
    }
}

static void store_xmm_snapshot(uint8_t dst[16][16]) {
    __asm__ volatile(
        "movdqu %%xmm0,  0(%0)\n\t"
        "movdqu %%xmm1, 16(%0)\n\t"
        "movdqu %%xmm2, 32(%0)\n\t"
        "movdqu %%xmm3, 48(%0)\n\t"
        "movdqu %%xmm4, 64(%0)\n\t"
        "movdqu %%xmm5, 80(%0)\n\t"
        "movdqu %%xmm6, 96(%0)\n\t"
        "movdqu %%xmm7,112(%0)\n\t"
        "movdqu %%xmm8,128(%0)\n\t"
        "movdqu %%xmm9,144(%0)\n\t"
        "movdqu %%xmm10,160(%0)\n\t"
        "movdqu %%xmm11,176(%0)\n\t"
        "movdqu %%xmm12,192(%0)\n\t"
        "movdqu %%xmm13,208(%0)\n\t"
        "movdqu %%xmm14,224(%0)\n\t"
        "movdqu %%xmm15,240(%0)\n\t"
        : : "r"(&dst[0][0])
        : "xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7",
          "xmm8", "xmm9", "xmm10", "xmm11", "xmm12", "xmm13", "xmm14", "xmm15", "memory");
}

static void load_xmm_seed(const uint8_t src[16][16]) {
    __asm__ volatile(
        "movdqu  0(%0), %%xmm0\n\t"
        "movdqu 16(%0), %%xmm1\n\t"
        "movdqu 32(%0), %%xmm2\n\t"
        "movdqu 48(%0), %%xmm3\n\t"
        "movdqu 64(%0), %%xmm4\n\t"
        "movdqu 80(%0), %%xmm5\n\t"
        "movdqu 96(%0), %%xmm6\n\t"
        "movdqu 112(%0), %%xmm7\n\t"
        "movdqu 128(%0), %%xmm8\n\t"
        "movdqu 144(%0), %%xmm9\n\t"
        "movdqu 160(%0), %%xmm10\n\t"
        "movdqu 176(%0), %%xmm11\n\t"
        "movdqu 192(%0), %%xmm12\n\t"
        "movdqu 208(%0), %%xmm13\n\t"
        "movdqu 224(%0), %%xmm14\n\t"
        "movdqu 240(%0), %%xmm15\n\t"
        : : "r"(&src[0][0])
        : "xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7",
          "xmm8", "xmm9", "xmm10", "xmm11", "xmm12", "xmm13", "xmm14", "xmm15");
}

static void print_hex_block(const char *label, const uint8_t data[16][16]) {
    for (int r = 0; r < 16; ++r) {
        printf("%s reg%02d=", label, r);
        for (int b = 0; b < 16; ++b) {
            printf("%02x", data[r][b]);
        }
        putchar('\n');
    }
}

static int run_case(struct xmm_case_result *r) {
    fill_seed(r->window.before);
    load_xmm_seed(r->window.before);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->getpid_ret)
        : "0"(SYS_getpid)
        : "rcx", "r11", "memory");

    store_xmm_snapshot(r->window.after_getpid);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->gettid_ret)
        : "0"(SYS_gettid)
        : "rcx", "r11", "memory");

    store_xmm_snapshot(r->window.after_gettid);

    long write_fd = 1;
    long write_len = 1;
    __asm__ volatile(
        "syscall\n"
        : "=a"(r->write_ret)
        : "0"(SYS_write), "D"(write_fd), "S"(&r->write_byte), "d"(write_len)
        : "rcx", "r11", "memory");

    store_xmm_snapshot(r->window.after_write);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->yield_ret)
        : "0"(SYS_sched_yield)
        : "rcx", "r11", "memory");

    store_xmm_snapshot(r->window.after_yield);

    return (r->getpid_ret > 0 && r->gettid_ret > 0 && r->write_ret == 1 && r->yield_ret == 0) ? 0 : 1;
}

int main(void) {
    struct xmm_case_result result = {0};
    result.write_byte = 'Z';

    int failed = run_case(&result);

    printf("case=vector.xmm-raw-syscall\n");
    printf("write-byte=0x%02x\n", (uint8_t)result.write_byte);
    printf("syscall-getpid-ret=%ld\n", result.getpid_ret);
    printf("syscall-gettid-ret=%ld\n", result.gettid_ret);
    printf("syscall-write-ret=%ld\n", result.write_ret);
    printf("syscall-yield-ret=%ld\n", result.yield_ret);

    print_hex_block("before", result.window.before);
    print_hex_block("after_getpid", result.window.after_getpid);
    print_hex_block("after_gettid", result.window.after_gettid);
    print_hex_block("after_write", result.window.after_write);
    print_hex_block("after_yield", result.window.after_yield);

    return failed;
}
