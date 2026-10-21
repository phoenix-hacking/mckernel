#include "fixture.h"
static unsigned long syscall_virt_to_phys_bridge(void *addr) { return virt_to_phys(addr); }
static long syscall_do_syscall_request_bridge(struct syscall_request *r,int cpu) { return do_syscall(r,cpu); }
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern int syscall_settid_body_result(struct syscall_request *request,
		int nr_tids, int *tids, int gettid_nr,
		syscall_virt_to_phys_fn_t virt_to_phys_fn,
		syscall_get_cpu_fn_t get_cpu_fn,
		syscall_request_call_fn_t syscall_fn, void (*log_fn)(int));

static void syscall_settid_log_bridge(int ret)
{
	kprintf("settid: WARNING: do_syscall returns %d\n", ret);
}
#endif

static int settid(struct thread *thread, int nr_tids, int *tids)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct syscall_request request IHK_DMA_ALIGN;

	return syscall_settid_body_result(&request, nr_tids, tids, __NR_gettid,
			syscall_virt_to_phys_bridge, ihk_mc_get_processor_id,
			syscall_do_syscall_request_bridge,
			syscall_settid_log_bridge);
#else
	int ret;
	struct syscall_request request IHK_DMA_ALIGN;

	memset(&request, 0, sizeof(request));

	request.number = __NR_gettid;
	/*
	 * If nr_tids is non-zero, tids should point to an array of ints
	 * where the thread ids of the mcexec process are expected.
	 */
	request.args[4] = nr_tids;
	request.args[5] = virt_to_phys(tids);
	if ((ret = do_syscall(&request, ihk_mc_get_processor_id())) < 0) {
		kprintf("%s: WARNING: do_syscall returns %d\n",
			__FUNCTION__, ret);
	}
	return ret;
#endif
}

int run_candidate(int n,int *t) { return settid(NULL,n,t); }
