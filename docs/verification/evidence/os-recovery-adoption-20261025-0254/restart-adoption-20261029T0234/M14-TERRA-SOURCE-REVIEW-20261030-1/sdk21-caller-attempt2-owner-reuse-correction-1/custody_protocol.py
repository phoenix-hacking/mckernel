"""Source-only custody handshake for fixed daemon/image observation.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
An actual direct-parent owner must supply verified identity, group, durable
publication and admission callbacks. This module does not create processes.
"""
import hashlib
import json
import math
import os
import select
import time

MAX_FRAME = 4096
PHASES = ('PARENT_READY', 'IMAGE_READY')
IDENTITY_KEYS = frozenset(('pid','birth','ppid','pgid','sid'))


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',', ':'),allow_nan=False).encode('ascii')


def valid_identity(row):
    return (isinstance(row,dict) and set(row)==IDENTITY_KEYS and
            all(type(row[k]) is int and row[k]>0 for k in IDENTITY_KEYS))


def make_event(nonce, phase, parent, child):
    if not isinstance(nonce,str) or len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('nonce invalid')
    if phase not in PHASES or not valid_identity(parent) or parent['pgid']!=parent['pid']:
        raise ValueError('phase, parent identity or owned group invalid')
    if phase=='PARENT_READY' and child is not None:
        raise ValueError('parent phase has child')
    if phase=='IMAGE_READY' and (not valid_identity(child) or child['pid']==parent['pid'] or
                                 child['ppid']!=parent['pid'] or child['pgid']!=parent['pgid'] or
                                 child['sid']!=parent['sid']):
        raise ValueError('child lineage differs')
    return {'version':1,'nonce':nonce,'phase':phase,'parent':parent,'child':child}


def ack_for(event):
    return {'version':1,'nonce':event['nonce'],'phase':event['phase'],
            'event_sha256':hashlib.sha256(canonical(event)).hexdigest()}


def validate_deadline(deadline):
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or deadline<=0:
        raise ValueError('deadline invalid')


def check_alive(deadline, clock, stopped):
    now=clock()
    if stopped() is not False or type(now) not in (int,float) or not math.isfinite(now) or now<=0 or now>=deadline:
        raise TimeoutError('custody expired or stopped')


def require_gate(gate):
    if gate() is not True: raise ValueError('admission gate did not explicitly pass')


def parent_handshake(event_fd, ack_fd, nonce, phase, parent, child, deadline, gate, stopped):
    # All I/O and callbacks also require an external, authoritative watchdog.
    validate_deadline(deadline)
    event=make_event(nonce,phase,parent,child)
    check_alive(deadline,time.monotonic,stopped)
    require_gate(gate)
    check_alive(deadline,time.monotonic,stopped)
    frame=canonical(event)+b'\n'
    if len(frame)>MAX_FRAME or os.write(event_fd,frame)!=len(frame): raise OSError('event write failed')
    data=bytearray()
    while True:
        check_alive(deadline,time.monotonic,stopped)
        ready,_,_=select.select([ack_fd],[],[],min(.05,max(0,deadline-time.monotonic())))
        if not ready: continue
        b=os.read(ack_fd,1)
        if not b: raise EOFError('custody acknowledgement missing')
        data.extend(b)
        if len(data)>MAX_FRAME: raise ValueError('custody acknowledgement oversized')
        if b==b'\n': break
    if bytes(data)!=canonical(ack_for(event))+b'\n': raise ValueError('custody acknowledgement differs')
    require_gate(gate)
    check_alive(deadline,time.monotonic,stopped)


def prepare_ack(event, expected_nonce, expected_phase, parent, child, deadline,
                clock, stopped, gate, held, observe, publish_durable):
    """Build ACK only after identity/census checks and durable publication.

    The real direct-parent owner supplies authenticated observations, checks,
    and a durable writer. This function does not implement a watchdog.
    """
    expected=make_event(expected_nonce,expected_phase,parent,child)
    if canonical(event)!=canonical(expected): raise ValueError('event differs')
    validate_deadline(deadline)
    wanted={r['pid']:r for r in (parent,child) if r is not None}
    def check():
        check_alive(deadline,clock,stopped)
        identities,members=observe()
        if (not isinstance(identities,dict) or any(type(pid) is not int or not valid_identity(row) for pid,row in identities.items()) or
            not isinstance(members,list) or any(type(pid) is not int for pid in members) or
            identities!=wanted or members!=sorted(wanted) or parent['pgid']!=parent['pid']):
            raise ValueError('identity or group differs')
        require_gate(gate)
        if held() is not True: raise ValueError('independent held-child binding unavailable')
        check_alive(deadline,clock,stopped)
    check()
    acknowledgement=ack_for(event)
    publish_durable({'event':event,'ack':acknowledgement})
    check()
    return canonical(acknowledgement)+b'\n'


class OuterProtocol:
    """Enforce single parent then image custody; unknown is never reset."""
    def __init__(self, nonce, parent, overall_deadline):
        validate_deadline(overall_deadline)
        self.overall_deadline=overall_deadline
        self.nonce=nonce
        self.parent=parent
        self.next_phase='PARENT_READY'
        self.unknown=False

    def accept(self,event,expected_child,clock,stopped,gate,held,observe,publish_durable):
        if self.unknown or self.next_phase is None:
            raise ValueError('custody is closed or unknown')
        try:
            # Child comes from the separately authenticated held-fork binding,
            # never from the event being checked. A live owner must establish
            # this fact and retain control of the actual GO channel.
            ack=prepare_ack(event,self.nonce,self.next_phase,self.parent,expected_child,
                            self.overall_deadline,clock,stopped,gate,held,observe,publish_durable)
        except BaseException:
            self.unknown=True
            raise
        self.next_phase='IMAGE_READY' if self.next_phase=='PARENT_READY' else None
        return ack
