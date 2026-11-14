int syscall_eventfd_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
		int eventfd_type)
{
	if (!packet)
		return -EINVAL;

	memset(packet, 0, sizeof(*packet));
	packet->msg = msg;
	packet->eventfd_type = eventfd_type;

	return 0;
}
int syscall_eventfd_send_result(void *channel, int msg, int eventfd_type,
		syscall_ikc_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;
	int prep_rc;

	if (!send_fn)
		return -EINVAL;

	prep_rc = syscall_eventfd_packet_prepare_result(&packet, msg,
			eventfd_type);
	if (prep_rc)
		return prep_rc;

	return send_fn(channel, &packet, 0);
}
static int syscall_ikc_send_bridge(void *channel, void *packet, int opt)
{
	return ihk_ikc_send((struct ihk_ikc_channel_desc *)channel, packet, opt);
}
void eventfd(int type)
{
	struct ihk_ikc_channel_desc *syscall_channel;

	syscall_channel = get_cpu_local_var(0)->ikc2linux;
	(void)syscall_eventfd_send_result(syscall_channel, SCD_MSG_EVENTFD,
			type, syscall_ikc_send_bridge);
}
