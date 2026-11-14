struct ihk_ikc_packet_header {
	struct ihk_ikc_channel_desc *channel;
};
struct syscall_request {
	/* TID of requesting thread */
	int rtid;
	/*
	 * TID of target thread. Remote page fault response needs to designate the
	 * thread that must serve the request, 0 indicates any thread from the pool
	 */
	int ttid;
	unsigned long valid;
	unsigned long number;
	unsigned long args[6];
};
enum mcctrl_os_cpu_operation {
	MCCTRL_OS_CPU_READ_REGISTER,
	MCCTRL_OS_CPU_WRITE_REGISTER,
	MCCTRL_OS_CPU_MAX_OP
};
struct ikc_scd_packet {
	struct ihk_ikc_packet_header header;
	int msg;
	int err;
	void *reply;
	union {
		/* for traditional SCD_MSG_* */
		struct {
			int ref;
			int osnum;
			int pid;
			unsigned long arg;
			struct syscall_request req;
			unsigned long resp_pa;
		};

		/* for SCD_MSG_SYSFS_* */
		struct {
			long sysfs_arg1;
			long sysfs_arg2;
			long sysfs_arg3;
		};

		/* SCD_MSG_WAKE_UP_SYSCALL_THREAD */
		struct {
			int ttid;
		};

		/* SCD_MSG_CPU_RW_REG */
		struct {
			unsigned long pdesc; /* Physical addr of the descriptor */
			enum mcctrl_os_cpu_operation op;
			void *resp;
		};

		/* SCD_MSG_EVENTFD */
		struct {
			int eventfd_type;
		};

		/* SCD_MSG_FUTEX_WAKE */
		struct {
			void *resp;
			int *spin_sleep; /* 1: waiting in linux_wait_event() 0: woken up by someone else */
		} futex;

		/* SCD_MSG_REMOTE_PAGE_FAULT */
		struct {
			int target_cpu;
			int fault_tid;
			unsigned long fault_address;
			unsigned long fault_reason;
		};
	};
	/* char padding[8]; */ /* We want the size to be 128 bytes */
};
