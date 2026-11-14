"""Source-only operation owner and watchdog decision engines.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No physical backend, global controller, CLI, or execution release is provided.
Every potentially blocking backend call must be governed by a separately running,
reviewed watchdog with authority over exact pinned identities. A group scan is
never descendant-retirement proof. Unknown ownership is always retained.
"""
import math
import threading
import custody_protocol as custody


def explicit(value, what):
    if value is not True: raise ValueError(what+' did not explicitly pass')


def valid_time(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0


def alive(ops, deadline):
    now=ops.now()
    if not valid_time(deadline) or not valid_time(now) or now>=deadline:
        raise TimeoutError('overall operation deadline expired or invalid')
    if ops.stop_state() is not False: raise InterruptedError('stop state present or unknown')
    explicit(ops.current_admission(), 'current admission')
    explicit(ops.watchdog_live(), 'external operation watchdog')


def scoped_watchdog_tick(ops, deadline, pinned):
    """One watchdog decision; the physical actor/loop is a review prerequisite.

    No group-wide signal is permitted here. A backend may signal only positively
    bound kernel-pinned handles. The state remains UNKNOWN on every intervention.
    """
    now=ops.now();stop=ops.stop_state()
    should_stop=(not valid_time(deadline) or not valid_time(now) or now>=deadline or stop is not False)
    if not should_stop: return 'CONTINUE'
    try:
        ops.record_unknown('WATCHDOG_STOP_OR_DEADLINE')
    finally:
        if pinned is not None and ops.pinned_identity_is_exact(pinned) is True:
            ops.signal_exact_pinned(pinned)
    return 'UNKNOWN_OWNERSHIP_RETAINED'


class OperationOwner:
    """One held root parent and at most one image child, no cleanup assertion.

    ops is a future reviewed physical backend. It must bind a fresh authenticated
    admission, sealed token, parent and child births/held gates, watchdog custody,
    nonblocking/bounded transport, raw streams, direct wait4 and independent
    descendant-retirement evidence. Callback return values alone prove none of
    those facts. In particular proc census is not a retirement witness.
    """
    def __init__(self, ops, nonce, deadline):
        custody.validate_deadline(deadline)
        self.ops=ops;self.nonce=nonce;self.deadline=deadline
        self.state='NEW';self.parent=None;self.child=None;self.pinned=None
        self._claim_lock=threading.Lock();self._claimed=False

    def gate(self):
        alive(self.ops,self.deadline)
        return True

    def _check_parent(self, row):
        if not custody.valid_identity(row) or row['pid']!=row['pgid']:
            raise ValueError('parent must be private-group leader')
        explicit(self.ops.parent_fork_binding(row), 'direct held-parent fork binding')
        explicit(self.ops.parent_go_control(row), 'held-parent GO control')

    def _custody_event(self, phase, expected_child, outer):
        self.gate()
        event=self.ops.receive_event(self.deadline)
        self.gate()
        if phase=='IMAGE_READY':
            if not custody.valid_identity(expected_child): raise ValueError('image fork identity missing')
            explicit(self.ops.image_fork_binding(self.parent,expected_child), 'image direct-fork binding')
        def held():
            return self.ops.held_go_control(phase,self.parent,expected_child)
        def observe():
            return self.ops.observe_owned_group(self.parent,expected_child)
        def publish(record):
            # Persist before the independent watchdog accepts this exact identity.
            explicit(self.ops.publish_custody(record), 'custody publication')
            explicit(self.ops.watchdog_adopt(record,self.deadline), 'watchdog custody acknowledgement')
        ack=outer.accept(event,expected_child,self.ops.now,self.ops.stop_state,
                         self.gate,held,observe,publish)
        self.gate()
        explicit(self.ops.send_ack(ack), 'custody ACK send')
        self.gate()

    def run(self):
        """Return a candidate observation or retained UNKNOWN; never clean up."""
        with self._claim_lock:
            if self._claimed:
                return {'status':self.state,'error':'OWNER_ALREADY_USED','current_free':False,'native_release':False}
            self._claimed=True
            self.state='ADMISSION_PENDING'
        fork_attempted=False
        try:
            self.gate()
            # This marker precedes fork: a thrown call may still have made a child.
            fork_attempted=True;self.state='FORK_OUTCOME_UNCERTAIN'
            held=self.ops.fork_held_parent(self.deadline)
            if not isinstance(held,dict) or set(held)!={'parent','pinned'}:
                raise ValueError('held parent result malformed')
            self.parent=held['parent'];self.pinned=held['pinned']
            self._check_parent(self.parent);self.gate()
            explicit(self.ops.publish_parent_start(self.parent), 'parent-start publication')
            explicit(self.ops.watchdog_adopt_parent(self.parent,self.pinned,self.deadline), 'watchdog parent custody')
            self.gate()
            # Backend seals the exact parent-group identity and fresh admission.
            explicit(self.ops.prepare_and_verify_release(self.parent,self.deadline), 'fresh operation release')
            self.gate()
            explicit(self.ops.release_parent_go(self.parent), 'held-parent GO')
            self.state='PARENT_RUNNING'
            outer=custody.OuterProtocol(self.nonce,self.parent,self.deadline)
            self._custody_event('PARENT_READY',None,outer)
            # Supplied from independent direct-fork/held-GO evidence, not event data.
            self.child=self.ops.read_bound_held_image(self.parent,self.deadline)
            self._custody_event('IMAGE_READY',self.child,outer)
            self.state='OBSERVING';self.gate()
            joined=self.ops.direct_wait_parent(self.parent,self.deadline)
            if (not isinstance(joined,dict) or set(joined)!={'pid','exit_status','reaped'} or
                type(joined['pid']) is not int or joined['pid']!=self.parent['pid'] or
                type(joined['exit_status']) is not int or joined['exit_status']!=0 or joined['reaped'] is not True):
                raise ValueError('direct parent wait/reap not established')
            self.gate()
            explicit(self.ops.streams_closed_and_captured(), 'complete raw streams')
            # This must be independently source-bound positive retirement evidence;
            # an empty or current group census is never sufficient.
            explicit(self.ops.descendant_retirement_proven(self.parent,self.child), 'descendant retirement')
            explicit(self.ops.final_evidence_durable(joined), 'final evidence publication')
            self.gate();self.state='CANDIDATE_OBSERVATION'
            return {'status':self.state,'current_free':False,'native_release':False}
        except BaseException as exc:
            self.state='UNKNOWN_OWNERSHIP_RETAINED' if fork_attempted else 'DENIED_BEFORE_FORK'
            try:
                self.ops.retain_unknown(self.state,type(exc).__name__,self.parent,self.child)
            except BaseException:
                pass
            # No inferred group cleanup and no signaling by the owner here.
            return {'status':self.state,'error':type(exc).__name__,'current_free':False,'native_release':False}
