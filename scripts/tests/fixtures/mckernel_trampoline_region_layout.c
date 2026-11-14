// SPDX-License-Identifier: GPL-2.0-only
/* Data-only exact Linux ABI witness. Never linked into the Rust module. */
#include <linux/build_bug.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/types.h>
#include <asm/e820/api.h>

static_assert(__builtin_types_compatible_p(typeof(&e820__mapped_raw_any),
              bool (*)(u64, u64, enum e820_type)));
static_assert(__builtin_types_compatible_p(typeof(&e820__mapped_any),
              bool (*)(u64, u64, enum e820_type)));
static_assert(__builtin_types_compatible_p(typeof(&__request_region),
              struct resource *(*)(struct resource *, resource_size_t,
                                   resource_size_t, const char *, int)));
static_assert(__builtin_types_compatible_p(typeof(&ioremap_cache),
              void __iomem *(*)(resource_size_t, unsigned long)));

const unsigned long long mckernel_trampoline_region_layout[]
__attribute__((used, section(".mckernel_trampoline_region_layout"))) = {
    sizeof(resource_size_t), sizeof(bool), sizeof(int), sizeof(enum e820_type),
    IORESOURCE_EXCLUSIVE, E820_TYPE_RAM,
};
