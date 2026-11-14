/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only real-TU witness: include after actual selected CPU source. The
 * existing declarations/data must be in scope, never substituted model types.
 */
#include "FUTURE-PRODUCTION-ABI.c.inc"
const unsigned long M14_C_WAKEUP_TYPE_ABI[22] = {
    sizeof(int), __alignof__(int),
    sizeof(unsigned int), __alignof__(unsigned int),
    sizeof(unsigned long), __alignof__(unsigned long),
    sizeof(first_page_va), __alignof__(__typeof__(first_page_va)),
    sizeof(*x86_wakeup_lapic_write_slot), __alignof__(__typeof__(*x86_wakeup_lapic_write_slot)),
    sizeof(*x86_wakeup_lapic_read_slot), sizeof(*x86_wakeup_wait_slot),
    sizeof(x86_issue_ipi),
    sizeof(x86_wakeup_lapic_write_slot), sizeof(x86_wakeup_lapic_read_slot),
    sizeof(x86_wakeup_wait_slot), sizeof(x86_wakeup_first_page_slot),
    sizeof(x86_wakeup_boot_status_slot),
    sizeof(x86_wakeup_constants), __alignof__(__typeof__(x86_wakeup_constants)),
    sizeof(cpu_boot_status), __alignof__(__typeof__(cpu_boot_status))
};
