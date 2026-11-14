static void __print_stack(struct stack *rbp, unsigned long first) {
	char buf[STACK_BUF_LEN];
	size_t len;

	/* Build string in buffer to output a single line */
	len = snprintf(buf, STACK_BUF_LEN,
		       "addr2line -e smp-x86/kernel/mckernel.img -fpia");

	if (first)
		len += snprintf(buf + len, STACK_BUF_LEN - len,
				" %#16lx", first);

	while ((unsigned long)rbp > 0xffff880000000000 &&
			STACK_BUF_LEN - len > sizeof(" 0x0123456789abcdef")) {
		len += snprintf(buf + len, STACK_BUF_LEN - len,
				" %#16lx", rbp->eip);
		rbp = rbp->rbp;
	}
	__kprintf("%s\n", buf);
}
