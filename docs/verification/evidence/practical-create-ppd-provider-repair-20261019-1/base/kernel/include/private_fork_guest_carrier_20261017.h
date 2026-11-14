/* SPDX-License-Identifier: GPL-2.0 */
#ifndef PRIVATE_FORK_GUEST_CARRIER_20261017_H
#define PRIVATE_FORK_GUEST_CARRIER_20261017_H
#include "process_helpers.h"
#include "private_fork_carrier_request_20261017.h"
/* Kernel-only registry capability, never a wire field or phase proof. */
struct process_fork_guest_carrier_handle { unsigned int slot, reserved; unsigned long epoch; };
typedef int (*process_fork_guest_carrier_visit_fn)(void *context,
    struct process_fork_inband_owner *owner, unsigned char *bytes,
    unsigned long physical, unsigned long nonce);
/* Exact original private constructor owns the supplied request. It keeps the
 * input ops table live and immutable through a local snapshot; the retained
 * context embeds that validated snapshot and never borrows the input table.
 * Every callback MUST be core-linked guest kernel text live for the entire
 * registry/escaped-owner lifetime, or have a separately retained actual module
 * pin. A const table or copying its function pointers does not pin code.
 * Failure does not change request, outputs, child references or CPU credits.
 * Success returns only a handle and retains disjoint heap owner/record/backing
 * in the kernel registry. No raw owner pointer escapes while private/freeable.
 * No successful transport exists until the real provider bridge is reviewed.
 */
int process_fork_guest_carrier_create(struct syscall_request *request,
    const struct process_fork_inband_ops *ops,
    struct process_fork_guest_carrier_handle *out);
/* First/link source receiver only: stages3/4 remain unavailable. Host bytes
 * may be accepted only AFTER the original actual do_syscall RET Acquire under
 * the genuine IHK-owned payload/ChildFork writer contract. This constructor
 * is not wired to weak prepare; parser success alone authenticates nothing.
 */
int process_fork_guest_carrier_create_first_link(struct syscall_request *request,
    struct process_fork_guest_carrier_handle *out);
/* Additive bounded cancellation receiver: only ORIGINAL UNPUBLISHED first RET
 * kind3/-125/sequence1, from actual backend drain + Mirror/TLB proof, may bind
 * the private revoke permit. Original caller alone performs checked cleanup;
 * literal2 cached by that actual destructor produces kind4/sequence2 through
 * real nr56 selector3 and actual final RET Acquire. Retry uses cached bytes
 * only; no child dereference or destructor retry. Caller/OS/kernel code and
 * parent lifetime stay pinned through in-band cleanup. The backing/record
 * remain retained across failed ACK and parent return; this introduces no
 * parent-death retry authority or postpositive/post-LINK revocation. Weak
 * prepare remains NULL; no runtime success path is activated. */
int process_fork_guest_carrier_create_abort_first(struct syscall_request *request,
    struct process_fork_guest_carrier_handle *out);
/* Metadata only: original private submission nonce from the live owned
 * registry carrier, strict NEWmarker physical/geometry match, no buffer read.
 * This is not a host-issued key or phase receipt and does not enable a caller.
 */
int process_fork_guest_carrier_request_nonce(struct process_fork_inband_owner *owner,
    const struct syscall_request *request, unsigned long *nonce);
/* Atomically expose the owner pointer only AFTER making storage nonfreeable.
 * Call before actual request publication. From here no cancellation/handoff
 * frees the backing; normal-child and final RET retirement remain unavailable.
 */
int process_fork_guest_carrier_begin(struct process_fork_guest_carrier_handle handle,
    struct process_fork_inband_owner **owner);
/* Sole pre-publication cancellation consumes registry ownership once. */
int process_fork_guest_carrier_cancel(struct process_fork_guest_carrier_handle handle);
int process_fork_guest_carrier_retain(struct process_fork_guest_carrier_handle handle);
/* Synchronous exclusive borrow. The trusted guest-kernel visitor may not retain
 * pointers after return. Other operations fail EBUSY while it runs. No lock
 * spans the visitor; registry ownership retains all storage across callbacks.
 * Caller independently holds actual request/RET byte ownership for the chosen
 * access direction; this borrow, selector and header confer no phase authority.
 */
int process_fork_guest_carrier_visit(struct process_fork_guest_carrier_handle handle,
    process_fork_guest_carrier_visit_fn visit, void *context);
#endif
