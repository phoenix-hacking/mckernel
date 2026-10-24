/* Declarative remaining C data debt: typed addresses of existing storage and
 * original macro values. No new state, getter or runtime C operation. */
void (**const x86_wakeup_lapic_write_slot)(int, unsigned int) = &lapic_write;
unsigned int (**const x86_wakeup_lapic_read_slot)(int) = &lapic_read;
void (**const x86_wakeup_wait_slot)(void) = &lapic_wait_icr_idle;
char **const x86_wakeup_first_page_slot = &first_page_va;
volatile int *const x86_wakeup_boot_status_slot = &cpu_boot_status;
const unsigned int x86_wakeup_constants[5] = {
    LAPIC_ESR, APIC_INT_LEVELTRIG, APIC_INT_ASSERT, APIC_DM_INIT, APIC_DM_STARTUP
};
