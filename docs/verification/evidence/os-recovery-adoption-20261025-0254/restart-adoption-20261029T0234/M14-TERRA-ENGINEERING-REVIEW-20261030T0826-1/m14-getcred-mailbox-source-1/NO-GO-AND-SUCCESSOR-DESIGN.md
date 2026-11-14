# Credential mailbox private candidate: NO-GO and bounded successor design

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The original private `credential.patch` SHA256
`bc106d2540afe062e7ac532ffe7c44dfce9ea31a05e5f54ef232ecdf9fb95bde` and all
fixture inputs/results remain preserved. Independent review found a liveness
failure; do not adopt, build, run physically, or expose this candidate. The
six earlier local extracted-method tests were executed before the NO-GO and are
not acceptance of cancellation or runtime correctness.

The candidate sets `cancelled` and returns `-EBUSY` for an unfinished credential
request. Existing `cancel_pending` and `close_worker` convert that failure into
whole-mailbox quarantine. `write_credentials` then rejects cancelled calls,
while all `return_value` outcomes require `credential_written`; no transition
can complete that response. A `pager_copy` failure after `prepare_payload` also
leaves the unique payload slot retained; unchanged retry hits EBUSY. Those facts
preserve unknown ownership but make no progress and can obstruct every call and
shutdown. They must not be described as a successful cancellation or cleanup.

The current guest `getcred_body_result` ignores the synchronous `do_syscall`
return; its refresh callers may read scratch even after a negative completion.
The old host mcexec branch also ignores GET_CRED ioctl errors and submits zero.
Therefore publishing a negative result alone is not safe for that old guest.
Quarantine/retain is an explicit possible failure state, not a liveness fix or
permission to clear the original owner. In particular no success, cancellation
ACK, guest wake or ownership release may be invented for an unknown effect.

A possible *separate*, default-off, independently reviewed successor needs both
ends and a real capability bound to the exact boot generation:

1. For the specifically selected Rust guest and its verified callers only,
   preserve the existing scratch/page and full request behavior but return NULL
   when the real synchronous offload returns a negative result. The existing
   Rust `syscall_refresh_cred_fields_body_result` checks NULL before reading
   scratch or changing its four fields. Never apply that assumption to legacy C
   callers that dereference the returned pointer unconditionally. Prove the
   actual selected guest and all callers, not only a source config label.
2. For that authenticated guest capability, the backend can model Pending,
   Ready and known terminal Failed(error) separately. Set Ready only after all
   32 stores complete with the claim retained. A known pre-effect failure may
   record its exact negative errno. If the launcher ignores GET_CRED's error and
   submits zero, the backend must produce the recorded negative, never success;
   check that the actual return and wake deliver that error to the guest before
   it inspects scratch. Cancellation is publishable as a negative only when the
   negotiated guest proof is live and no writes remain in flight.
3. If a claim was acquired, keep it until actual final response publication.
   A known stopped copy that failed after claim may transition to Failed for the
   error-aware guest without retrying the occupied payload; the guest must not
   read partial bytes. An uncertain/ongoing copy, uncertain publication or lost
   capability retains/quarantines the exact response and claim; do not assume a
   terminal write or remove a tag from an error path.
4. Legacy/non-negotiated guests cannot use negative completion as proof of safe
   scratch handling. Preserve their existing working predecessor route or retain
   an uninitialized credential response; do not silently apply error-aware
   semantics or publish a fabricated acknowledgement.
5. `do_setresuid`/`do_setresgid` currently call a void refresh path and discard
   the refresh-helper status after the underlying host credential change. A
   NULL guard prevents uninitialized reads but does not by itself resolve stale
   cached credentials or propagate a failure to the syscall caller. Review this
   functional consequence and its ABI before claiming successful error handling.

The actual OS/boot generation, current task and MM, original request/worker/
delivery, credential source and full payload claim must remain tied throughout;
process registration is shared across same-TGID file contexts and does not prove
the exact FD that issued WAIT. No capability negotiation, guest change, backend
state transition, C/Rust source integration, emitted ABI or native evidence is
implemented by this design. Source-only work requires independent review and
meaningful failure/cancellation/publication tests before any release.
