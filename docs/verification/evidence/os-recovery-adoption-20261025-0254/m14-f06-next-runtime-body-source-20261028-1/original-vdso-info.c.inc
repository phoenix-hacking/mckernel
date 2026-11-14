int vdso_get_vdso_info(void)
{
	int error;
	struct ikc_scd_packet packet;
	struct ihk_ikc_channel_desc *ch = get_this_cpu_local_var()->ikc2linux;

	dkprintf("vdso_get_vdso_info()\n");
	memset(&vdso, '\0', sizeof vdso);
	vdso.busy = 1;
	vdso.vdso_npages = 0;

	error = x86_vdso_packet_prepare_result(&packet, SCD_MSG_GET_VDSO_INFO,
			virt_to_phys(&vdso));
	if (error) {
		ekprintf("vdso_get_vdso_info: packet prepare failed. %d\n",
				error);
		goto out;
	}

	error = ihk_ikc_send(ch, &packet, 0);
	if (error) {
		ekprintf("vdso_get_vdso_info: ihk_ikc_send failed. %d\n", error);
		goto out;
	}

	while (vdso.busy) {
		cpu_pause();
	}

	error = 0;
out:
	if (error) {
		vdso.vdso_npages = 0;
	}
	dkprintf("vdso_get_vdso_info(): %d\n", error);
	return error;
} /* vdso_get_vdso_info() */
