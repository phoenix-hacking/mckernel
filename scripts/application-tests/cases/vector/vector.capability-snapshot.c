#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

struct cpuid_regs {
    uint32_t eax;
    uint32_t ebx;
    uint32_t ecx;
    uint32_t edx;
};

static void cpuid_leaf(uint32_t leaf, uint32_t subleaf, struct cpuid_regs *out) {
    __asm__ volatile("cpuid"
                     : "=a"(out->eax), "=b"(out->ebx), "=c"(out->ecx), "=d"(out->edx)
                     : "a"(leaf), "c"(subleaf)
                     : "cc");
}

static int xgetbv_if_allowed(uint32_t leaf1_ecx, uint64_t *xcr0) {
    const uint32_t xsave_mask = (1u << 26);
    const uint32_t osxsave_mask = (1u << 27);
    if ((leaf1_ecx & (xsave_mask | osxsave_mask)) != (xsave_mask | osxsave_mask)) {
        *xcr0 = 0ULL;
        return 0;
    }
    uint32_t eax;
    uint32_t edx;
    __asm__ volatile("xgetbv"
                     : "=a"(eax), "=d"(edx)
                     : "c"(0)
                     : "cc");
    *xcr0 = ((uint64_t)edx << 32) | eax;
    return 1;
}

static void trim_newline(char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\n') {
        line[n - 1] = 0;
    }
}

static void read_proc_cpuinfo_line(const char *key, char *out, size_t out_sz) {
    FILE *fp = fopen("/proc/cpuinfo", "r");
    if (!fp) {
        snprintf(out, out_sz, "<missing-cpuinfo>");
        return;
    }

    char *line = NULL;
    size_t cap = 0;
    size_t key_len = strlen(key);
    int found = 0;

    while (getline(&line, &cap, fp) != -1) {
        if (strncmp(line, key, key_len) == 0 && line[key_len] == ':') {
            const char *value = line + key_len;
            while (*value == ':' || *value == ' ' || *value == '\t') {
                ++value;
            }
            snprintf(out, out_sz, "%s", value);
            trim_newline(out);
            found = 1;
            break;
        }
    }

    if (!found) {
        snprintf(out, out_sz, "<missing:%s>", key);
    }
    free(line);
    fclose(fp);
}

int main(void) {
    struct cpuid_regs leaf0 = {0};
    struct cpuid_regs leaf1 = {0};
    struct cpuid_regs leaf7[16] = {{0}};
    struct cpuid_regs leafd[32] = {{0}};

    cpuid_leaf(0, 0, &leaf0);
    cpuid_leaf(1, 0, &leaf1);

    uint32_t max_leaf0 = leaf0.eax;
    uint32_t max_leaf7 = 0;
    for (uint32_t sub = 0; sub < 16; ++sub) {
        cpuid_leaf(7, sub, &leaf7[sub]);
        if (leaf7[sub].eax == 0 && leaf7[sub].ebx == 0 && leaf7[sub].ecx == 0 && leaf7[sub].edx == 0) {
            break;
        }
        max_leaf7 = sub;
    }

    uint32_t leafd_supported = 0;
    for (uint32_t sub = 0; sub < 32; ++sub) {
        cpuid_leaf(0xD, sub, &leafd[sub]);
        if (leafd[sub].eax == 0 && leafd[sub].ebx == 0 && leafd[sub].ecx == 0 && leafd[sub].edx == 0) {
            break;
        }
        leafd_supported = sub;
    }

    uint64_t xcr0 = 0;
    int xgetbv_ok = xgetbv_if_allowed(leaf1.ecx, &xcr0);

    char vendor[256];
    char brand[256];
    char model_name[256];
    read_proc_cpuinfo_line("vendor_id", vendor, sizeof(vendor));
    read_proc_cpuinfo_line("model name", model_name, sizeof(model_name));
    read_proc_cpuinfo_line("cpu family", brand, sizeof(brand));

    printf("case=vector.capability-snapshot\n");
    printf("cpuid-leaf0-max=0x%x\n", max_leaf0);
    printf("leaf1-eax=0x%x\n", leaf1.eax);
    printf("leaf1-ebx=0x%x\n", leaf1.ebx);
    printf("leaf1-ecx=0x%x\n", leaf1.ecx);
    printf("leaf1-edx=0x%x\n", leaf1.edx);
    printf("leaf1-xsave-bit=0x%x leaf1-osxsave-bit=0x%x\n", (leaf1.ecx >> 26) & 1u, (leaf1.ecx >> 27) & 1u);

    for (uint32_t sub = 0; sub <= max_leaf7; ++sub) {
        printf("leaf7-sub%u-eax=0x%x ebx=0x%x ecx=0x%x edx=0x%x\n", sub,
               leaf7[sub].eax, leaf7[sub].ebx, leaf7[sub].ecx, leaf7[sub].edx);
    }

    for (uint32_t sub = 0; sub <= leafd_supported; ++sub) {
        printf("leafD-sub%u-eax=0x%x ebx=0x%x ecx=0x%x edx=0x%x\n", sub,
               leafd[sub].eax, leafd[sub].ebx, leafd[sub].ecx, leafd[sub].edx);
    }

    if (xgetbv_ok) {
        printf("xgetbv0=0x%016llx\n", (unsigned long long)xcr0);
    } else {
        printf("xgetbv0=BLOCKED: missing XSAVE or OSXSAVE\n");
    }

    printf("qemu-cpu-vendor=%s\n", vendor);
    printf("qemu-cpu-branch=%s\n", brand);
    printf("qemu-cpu-model=%s\n", model_name);
    return 0;
}
