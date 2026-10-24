static void set_warm_reset_vector(unsigned long ip)
{
	x86_set_warm_reset(ip, first_page_va);
}

static void __x86_wakeup(int apicid, unsigned long ip)
{
	int retry = 3;

	set_warm_reset_vector(ip);

	/* Clear the error */
	lapic_write(LAPIC_ESR, 0);
	lapic_read(LAPIC_ESR);

	/* INIT */
	x86_issue_ipi(apicid, 
	              APIC_INT_LEVELTRIG | APIC_INT_ASSERT | APIC_DM_INIT);

	x86_issue_ipi(apicid, 
	              APIC_INT_LEVELTRIG | APIC_DM_INIT);
	lapic_wait_icr_idle();

	while (retry--) {
		lapic_read(LAPIC_ESR);
		x86_issue_ipi(apicid, APIC_DM_STARTUP | (ip >> 12));
		lapic_wait_icr_idle();

		arch_delay(200);

		if (cpu_boot_status) 
			break;
	}
}
