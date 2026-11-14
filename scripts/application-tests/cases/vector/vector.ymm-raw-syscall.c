#include <stdio.h>
#include <stdint.h>
#include <sys/syscall.h>

struct ymm_window {
    uint8_t before[16][32];
    uint8_t after_getpid[16][32];
    uint8_t after_gettid[16][32];
    uint8_t after_write[16][32];
    uint8_t after_yield[16][32];
};

struct ymm_case_result {
    struct ymm_window window;
    long getpid_ret;
    long gettid_ret;
    long write_ret;
    long yield_ret;
    char write_byte;
};

static void fill_seed(uint8_t out[16][32]) {
    for (uint32_t reg = 0; reg < 16; ++reg) {
        for (uint32_t b = 0; b < 32; ++b) {
            out[reg][b] = (uint8_t)((reg * 0x11u + b * 0x0Bu + 0xA5u) & 0xFFu);
        }
    }
}

static void store_ymm_snapshot(uint8_t dst[16][32]) {
    __asm__ volatile(
        "vmovdqu %%ymm0,  0(%0)\n\t"
        "vmovdqu %%ymm1, 32(%0)\n\t"
        "vmovdqu %%ymm2, 64(%0)\n\t"
        "vmovdqu %%ymm3, 96(%0)\n\t"
        "vmovdqu %%ymm4,128(%0)\n\t"
        "vmovdqu %%ymm5,160(%0)\n\t"
        "vmovdqu %%ymm6,192(%0)\n\t"
        "vmovdqu %%ymm7,224(%0)\n\t"
        "vmovdqu %%ymm8,256(%0)\n\t"
        "vmovdqu %%ymm9,288(%0)\n\t"
        "vmovdqu %%ymm10,320(%0)\n\t"
        "vmovdqu %%ymm11,352(%0)\n\t"
        "vmovdqu %%ymm12,384(%0)\n\t"
        "vmovdqu %%ymm13,416(%0)\n\t"
        "vmovdqu %%ymm14,448(%0)\n\t"
        "vmovdqu %%ymm15,480(%0)\n\t"
        : : "r"(&dst[0][0])
        : "ymm0", "ymm1", "ymm2", "ymm3", "ymm4", "ymm5", "ymm6", "ymm7",
          "ymm8", "ymm9", "ymm10", "ymm11", "ymm12", "ymm13", "ymm14", "ymm15", "memory");
}

static void load_ymm_seed(const uint8_t src[16][32]) {
    __asm__ volatile(
        "vmovdqu  0(%0), %%ymm0\n\t"
        "vmovdqu 32(%0), %%ymm1\n\t"
        "vmovdqu 64(%0), %%ymm2\n\t"
        "vmovdqu 96(%0), %%ymm3\n\t"
        "vmovdqu 128(%0), %%ymm4\n\t"
        "vmovdqu 160(%0), %%ymm5\n\t"
        "vmovdqu 192(%0), %%ymm6\n\t"
        "vmovdqu 224(%0), %%ymm7\n\t"
        "vmovdqu 256(%0), %%ymm8\n\t"
        "vmovdqu 288(%0), %%ymm9\n\t"
        "vmovdqu 320(%0), %%ymm10\n\t"
        "vmovdqu 352(%0), %%ymm11\n\t"
        "vmovdqu 384(%0), %%ymm12\n\t"
        "vmovdqu 416(%0), %%ymm13\n\t"
        "vmovdqu 448(%0), %%ymm14\n\t"
        "vmovdqu 480(%0), %%ymm15\n\t"
        : : "r"(&src[0][0])
        : "ymm0", "ymm1", "ymm2", "ymm3", "ymm4", "ymm5", "ymm6", "ymm7",
          "ymm8", "ymm9", "ymm10", "ymm11", "ymm12", "ymm13", "ymm14", "ymm15");
}

static void print_hex_block(const char *label, const uint8_t data[16][32]) {
    for (int r = 0; r < 16; ++r) {
        printf("%s reg%02d=", label, r);
        for (int b = 0; b < 32; ++b) {
            printf("%02x", data[r][b]);
        }
        putchar('\n');
    }
}

static int run_case(struct ymm_case_result *r) {
    fill_seed(r->window.before);
    load_ymm_seed(r->window.before);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->getpid_ret)
        : "0"(SYS_getpid)
        : "rcx", "r11", "memory");

    store_ymm_snapshot(r->window.after_getpid);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->gettid_ret)
        : "0"(SYS_gettid)
        : "rcx", "r11", "memory");

    store_ymm_snapshot(r->window.after_gettid);

    long write_fd = 1;
    long write_len = 1;
    __asm__ volatile(
        "syscall\n"
        : "=a"(r->write_ret)
        : "0"(SYS_write), "D"(write_fd), "S"(&r->write_byte), "d"(write_len)
        : "rcx", "r11", "memory");

    store_ymm_snapshot(r->window.after_write);

    __asm__ volatile(
        "syscall\n"
        : "=a"(r->yield_ret)
        : "0"(SYS_sched_yield)
        : "rcx", "r11", "memory");

    store_ymm_snapshot(r->window.after_yield);

    return (r->getpid_ret > 0 && r->gettid_ret > 0 && r->write_ret == 1 && r->yield_ret == 0) ? 0 : 1;
}

int main(void) {
    struct ymm_case_result result = {0};
    result.write_byte = 'Y';

    int failed = run_case(&result);

    printf("case=vector.ymm-raw-syscall\n");
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
