/* Functional OS/apps and Rust migration only; no security testing.
 * Append to the accepted hoststub fixture only after root grant; not a second queue. */
#include <stddef.h>
#include <assert.h>
#include <ihk/ihk_rusage.h>
extern size_t ihklib_mcstat_rusage_size(void);
extern size_t ihklib_mcstat_rusage_threads_offset(void);
extern size_t ihklib_mcstat_request_size(void);
struct actual_rusage_request {struct ihk_os_rusage *rusage;size_t size_rusage;};
static void check_actual_rust_mcstat_abi(void) {
 assert(ihklib_mcstat_rusage_size()==sizeof(struct ihk_os_rusage));
 assert(ihklib_mcstat_rusage_threads_offset()==offsetof(struct ihk_os_rusage,num_threads));
 assert(ihklib_mcstat_request_size()==sizeof(struct actual_rusage_request));
}
/* Exact consumer vectors to append to existing mocks:
 * 1) null and each wrong size: -EFAULT/-EINVAL before any access/open/ioctl/close.
 * 2) access and open errors at /dev/mcos-7; close negative returned errno except -1.
 * 3) GET_NUM_NUMA_NODES: raw positive/zero values, negative ioctl -> captured -errno.
 * 4) GETRUSAGE: request's exact original buffer pointer/size; untouched buffer and
 *    driver partial writes on both success and error are preserved byte-for-byte.
 * 5) nonzero +/- ioctl errors: -errno captured before close clobbers it; exactly
 *    one request/close, no allocations or buffer ownership transfer.
 * 6) selected ENABLE_RUSAGE=1 path and separately declared disabled cfg stub,
 *    which returns -ENOSYS before validation/IO (not current profile acceptance).
 * Keep original C vs Rust event/error/output equality, no synthetic native credit.
 */
