// SPDX-License-Identifier: GPL-2.0-only
/* Data-only witness from the exact control-kernel headers; no runtime body. */
#include <linux/build_bug.h>
#include <linux/irq_work.h>
#include <linux/stddef.h>
#ifdef MCKERNEL_IRQ_REMOTE_WITNESS
#include <linux/percpu.h>
#include <linux/sched.h>
#include <asm/apic.h>
DECLARE_PER_CPU(struct llist_head, raised_list);
static_assert(__builtin_types_compatible_p(__typeof__(&per_cpu_ptr_to_phys),
                                         phys_addr_t (*)(void *)));
static_assert(__builtin_types_compatible_p(__typeof__(&irq_work_sync),
                                         void (*)(struct irq_work *)));
static_assert(__builtin_types_compatible_p(__typeof__(&__SCT__apic_call_send_IPI_mask),
                                         void (*)(const struct cpumask *, int)));
static_assert(IRQ_WORK_VECTOR == 0xf6);
const unsigned long mckernel_irq_transport_layout[]
__attribute__((used, section(".mckernel_irq_transport"))) = {
    sizeof(struct llist_head), __alignof__(struct llist_head),
    sizeof(struct cpumask), offsetof(struct cpumask, bits),
    offsetof(struct task_struct, thread_info.cpu), IRQ_WORK_VECTOR,
};
#endif

static_assert(sizeof(struct irq_work) == 32);
static_assert(__alignof__(struct irq_work) == 8);
static_assert(offsetof(struct irq_work, node.llist) == 0);
static_assert(offsetof(struct irq_work, node.a_flags) == 8);
static_assert(offsetof(struct irq_work, node.src) == 12);
static_assert(offsetof(struct irq_work, node.dst) == 14);
static_assert(offsetof(struct irq_work, func) == 16);
static_assert(offsetof(struct irq_work, irqwait) == 24);
static_assert(sizeof(((struct irq_work *)0)->node.a_flags) == 4);

const unsigned long mckernel_irq_work_layout[]
__attribute__((used, section(".mckernel_irq_layout"))) = {
	sizeof(struct irq_work), __alignof__(struct irq_work),
	offsetof(struct irq_work, node.llist),
	offsetof(struct irq_work, node.a_flags),
	offsetof(struct irq_work, node.src),
	offsetof(struct irq_work, node.dst),
	offsetof(struct irq_work, func),
	offsetof(struct irq_work, irqwait),
	sizeof(((struct irq_work *)0)->node.a_flags),
	IRQ_WORK_PENDING, IRQ_WORK_BUSY, CSD_TYPE_IRQ_WORK,
};
