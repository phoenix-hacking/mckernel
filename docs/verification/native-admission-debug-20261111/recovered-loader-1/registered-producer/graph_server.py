"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One graph protocol handler; requires actual owned graph producer and caller binding.
No listener, mount, launch, cleanup, or physical release exists in this module.
"""
import os
import socket
import struct
import time
import custody_protocol_v2 as wire
import graph_observations as obs
from graph_producer import GraphProducer
from ownership_latch import CustodyLatch


def fail(message): raise ValueError(message)


def birth(pid):
    fields = open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()
    if len(fields) < 20 or fields[0] in ('Z','X','x'): fail('consumer unavailable')
    return int(fields[1]), fields[19]


class GraphChannel:
    """Bound channel handler; owner must keep process and custody alive."""
    def __init__(self, sock, producer, consumer_pid, consumer_birth, deadline, max_age, max_step, latch):
        if type(latch) is not CustodyLatch:fail('operation failure latch required')
        self.op_latch=latch
        if type(producer) is not GraphProducer or producer.state != 'OBSERVED_NOT_RELEASED':
            fail('no actually observed owned producer')
        if os.geteuid() != 0 or birth(consumer_pid) != (os.getpid(), consumer_birth):
            fail('consumer must be a live direct child')
        if sock.family != socket.AF_UNIX or sock.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE) != socket.SOCK_STREAM:
            fail('wrong socket')
        peer = struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if peer[0] != os.getpid() or peer[1] != 0:
            fail('socketpair must be created by this root supervisor before fork')
        if type(max_age) not in (int,float) or not 0 < max_age <= 30:
            fail('invalid freshness')
        self.sock,self.producer,self.consumer_pid,self.consumer_birth = sock,producer,consumer_pid,consumer_birth
        if type(max_step) not in (int,float) or not 0 < max_step <= 600: fail('reviewed finite operation limit required')
        self.deadline,self.max_age,self.max_step = deadline,max_age,max_step
        self.sequence=0; self.challenge=None; self.last_expiry=None

    def handle_one(self):
        p = self.producer
        token=self.op_latch.begin('GRAPH_HELD')
        now = wire.boot_now()
        if now >= self.deadline or birth(self.consumer_pid) != (os.getpid(),self.consumer_birth):
            p.state='UNKNOWN_RETAINED'; fail('consumer or deadline changed')
        operation_deadline=min(self.deadline, now+self.max_step, self.last_expiry if self.last_expiry is not None else self.deadline)
        try:
            message=wire.receive(self.sock,operation_deadline)
            self.sequence+=1
            operation='graph-observe-v1' if self.sequence == 1 else 'graph-revalidate-v1'
            request=wire.validate(message,'graph',operation,p.lease.nonce,self.sequence,p.lease.lease_sha256,p.custody_sha256)
            if type(request) is not dict: fail('bad graph request')
            if self.sequence == 1:
                if set(request) != {'challenge','consumer_pid','consumer_birth','boot_id','contract_sha256'}:
                    fail('observe request shape')
                wire.sha256_hex(request['challenge'])
                if (request['consumer_pid'] != self.consumer_pid or request['consumer_birth'] != self.consumer_birth or
                    request['boot_id'] != p.boot_id or request['contract_sha256'] != obs.CONTRACT_SHA):
                    fail('observe request binding')
                self.challenge=request['challenge']
            else:
                if set(request) != {'type','nonce','original_nonce','candidate_sha256','lease_sha256','custody_sha256'}:
                    fail('revalidation shape')
                wire.sha256_hex(request['nonce'])
                if (request['type'] != 'graph-revalidate-v1' or request['original_nonce'] != self.challenge or
                    request['candidate_sha256'] != p.data_sha256 or request['lease_sha256'] != p.lease.lease_sha256 or
                    request['custody_sha256'] != p.custody_sha256):
                    fail('revalidation binding')
            # This independently repeats the real graph/FD/lease observations.
            p.reobserve()
            observed = wire.boot_now()
            expiry=min(self.deadline,observed+self.max_age)
            if observed >= operation_deadline or birth(self.consumer_pid) != (os.getpid(),self.consumer_birth):
                fail('observation expired or consumer changed')
            if self.sequence == 1:
                response=dict(type='graph-observation-v1',nonce=self.challenge,boot_id=p.boot_id,
                     provider_pid=os.getpid(),provider_birth=birth(os.getpid())[1],consumer_pid=self.consumer_pid,
                     consumer_birth=self.consumer_birth,lease_sha256=p.lease.lease_sha256,observed_boot=observed,
                     expires_boot=expiry,custody_sha256=p.custody_sha256,candidate=p.data)
            else:
                response=dict(type='graph-custody-held-v1',nonce=request['nonce'],original_nonce=self.challenge,
                     candidate_sha256=p.data_sha256,lease_sha256=p.lease.lease_sha256,custody_sha256=p.custody_sha256,
                     observed_boot=observed,expires_boot=expiry)
            p.union.verify_owner()
            self.op_latch.publish(token,lambda:wire.send(self.sock,
                wire.envelope('graph',operation,p.lease.nonce,self.sequence,p.lease.lease_sha256,
                              p.custody_sha256,response),operation_deadline))
            p.union.verify_owner()
            self.last_expiry=expiry
        except BaseException:
            p.state='UNKNOWN_RETAINED'
            raise
