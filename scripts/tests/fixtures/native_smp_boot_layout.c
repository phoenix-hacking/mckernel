/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact-header data witness only; never linked into a project module. */
#include <linux/build_bug.h>
#include <linux/moduleparam.h>
#include <linux/percpu.h>
#include <linux/timekeeping.h>
#include <linux/version.h>
#include <asm/apic.h>
#include <asm/numa.h>
#include <asm/pgtable.h>
#include <asm/smp.h>
#include <asm/tsc.h>
#include "config.h"
#define IHK_IKC_USE_LINUX_WORK_IRQ 1
#ifndef BOOT_WITHOUT_PERF
#define ENABLE_PERF 1
#endif
#include "../../../ihk/cokernel/smp/x86_64/bootparam.h"

static_assert(__builtin_types_compatible_p(typeof(&wakeup_secondary_cpu_via_init),
              int (*)(u32, unsigned long, unsigned int)));
static_assert(__builtin_types_compatible_p(typeof(&per_cpu_ptr_to_phys),
              phys_addr_t (*)(void *)));
static_assert(__builtin_types_compatible_p(typeof(&ktime_get_real_ts64),
              void (*)(struct timespec64 *)));
static_assert(__builtin_types_compatible_p(typeof(&kernel_param_lock),
              void (*)(struct module *)));
static_assert(__builtin_types_compatible_p(typeof(&kernel_param_unlock),
              void (*)(struct module *)));
static_assert(__builtin_types_compatible_p(typeof(&__node_distance), int (*)(int, int)));
static_assert(__builtin_types_compatible_p(typeof(&tsc_khz), unsigned int *));
static_assert(sizeof(init_top_pgt[0]) == 8);
static_assert(__builtin_types_compatible_p(typeof(&__SCT__apic_call_send_IPI_mask),
              void (*)(const struct cpumask *, int)));
static_assert(__builtin_types_compatible_p(typeof(apic), struct apic *));

#define OFFSET(field) offsetof(struct smp_boot_param, field)
const unsigned long long native_smp_boot_layout[]
__attribute__((used, section(".mckernel_native_boot_layout"))) = {
    sizeof(struct smp_boot_param), __alignof__(struct smp_boot_param),
    OFFSET(start), OFFSET(end), OFFSET(status), OFFSET(param_size),
    OFFSET(bootstrap_mem_end), OFFSET(msg_buffer), OFFSET(msg_buffer_size),
    OFFSET(mikc_queue_recv), OFFSET(mikc_queue_send),
    OFFSET(linux_kernel_pgt_phys), OFFSET(page_offset_base), OFFSET(ident_table),
    OFFSET(ns_per_tsc), OFFSET(boot_tsc), OFFSET(boot_sec), OFFSET(boot_nsec),
    OFFSET(ihk_ikc_cpu_raised_list), OFFSET(ikc_irq_work_func), OFFSET(ihk_ikc_irq),
    OFFSET(ihk_ikc_irq_apicids), OFFSET(kernel_args), OFFSET(nr_linux_cpus),
    OFFSET(nr_cpus), OFFSET(nr_numa_nodes), OFFSET(nr_memory_chunks), OFFSET(osnum),
    OFFSET(dump_level), OFFSET(linux_default_huge_page_shift), OFFSET(dump_page_set),
    sizeof(struct ihk_smp_boot_param_cpu),
    sizeof(struct ihk_smp_boot_param_numa_node),
    sizeof(struct ihk_smp_boot_param_memory_chunk),
    sizeof(struct ihk_dump_page), sizeof(struct ihk_dump_page_set),
    offsetof(struct ihk_dump_page_set, count),
    offsetof(struct ihk_dump_page_set, page_size),
    offsetof(struct ihk_dump_page_set, phy_page),
};
