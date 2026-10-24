/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY, append to a future selected complete CPU TU witness.
 * Real original declarations/data are in scope; no model struct/layout.
 */
_Static_assert(sizeof(int)==4 && sizeof(unsigned int)==4 && sizeof(unsigned long)==8,
               "actual callback integer transport");
_Static_assert(sizeof(void*)==8 && sizeof(x86_issue_ipi)==8,
               "actual data/function pointer transport");
_Static_assert(__builtin_types_compatible_p(__typeof__(*x86_wakeup_lapic_write_slot),
                                          void(*)(int,unsigned int)), "existing write slot");
_Static_assert(__builtin_types_compatible_p(__typeof__(*x86_wakeup_lapic_read_slot),
                                          unsigned int(*)(int)), "existing read slot");
_Static_assert(__builtin_types_compatible_p(__typeof__(*x86_wakeup_wait_slot),
                                          void(*)(void)), "existing wait slot");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_issue_ipi),
                                          void(*)(unsigned int,unsigned int)), "existing IPI slot");
_Static_assert(sizeof(x86_wakeup_constants)==20,"actual five macro-data words");
_Static_assert(sizeof(x86_wakeup_lapic_write_slot)==8 && sizeof(x86_wakeup_lapic_read_slot)==8 &&
               sizeof(x86_wakeup_wait_slot)==8 && sizeof(x86_wakeup_first_page_slot)==8 &&
               sizeof(x86_wakeup_boot_status_slot)==8,"five exact pointer descriptors");
typedef void(*M14WakeupEntry)(int,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&__x86_wakeup),M14WakeupEntry),
               "actual existing wakeup callers int/unsigned-long ABI");
