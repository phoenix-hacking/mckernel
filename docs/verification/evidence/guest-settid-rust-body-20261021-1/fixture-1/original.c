#include "fixture.h"
static int settid(struct thread *thread, int nr_tids, int *tids)
{
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
}


int run_original(int n,int *t) { return settid(NULL,n,t); }
