"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only direct graph producer, with no execution or release entry point.
"""
import fcntl
import hashlib
import json
import os
import stat
import time
import graph_observations as obs
from ownership_latch import CustodyLatch
import custody_protocol_v2 as wire
import inplace_custody as source
from union_server_guarded import UnionChannel
import adapter
import immutable_epoch


def fail(message): raise ValueError(message)


def file_key(fd):
    s = os.fstat(fd)
    return {'device':s.st_dev, 'inode':s.st_ino, 'mode':stat.S_IMODE(s.st_mode), 'uid':s.st_uid}


def cap(caps, boot_id):
    if (type(caps) is not dict or set(caps) != {'utc','boot','mono','boot_id'} or
        boot_id != '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' or caps['boot_id'] != boot_id):
        fail('clock binding')
    actual = (time.time(), time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic())
    bounds = (1793774133, 1571567.6959065471, 1556229.568859425)
    for key, now, bound in zip(('utc','boot','mono'), actual, bounds):
        v = caps[key]
        if type(v) not in (int,float) or not now < v <= bound: fail('expired or widened cap')


class RootLease:
    """Root-owned operation-specific lease. No cleanup or release method."""
    def __init__(self, fd, root_fd, nonce, lock_owner_pid, lock_owner_birth):
        if os.geteuid() != 0: fail('root supervisor required')
        wire.sha256_hex(nonce)
        if type(lock_owner_pid) is not int or lock_owner_pid != os.getppid() or obs.process(lock_owner_pid)[0] != lock_owner_birth:
            fail('live watchdog parent birth required')
        self.lock_owner_pid,self.lock_owner_birth=lock_owner_pid,lock_owner_birth
        root = os.fstat(root_fd); lease = os.fstat(fd)
        if (not stat.S_ISDIR(root.st_mode) or root.st_uid != 0 or stat.S_IMODE(root.st_mode) & 0o077 or
            not stat.S_ISREG(lease.st_mode) or lease.st_uid != 0 or stat.S_IMODE(lease.st_mode) & 0o077 or lease.st_nlink != 1):
            fail('lease ancestry or identity')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.fd, self.root_fd, self.nonce = fd, root_fd, nonce
        self.identity = file_key(fd)
        self.root_identity = file_key(root_fd)
        self.lease_sha256 = hashlib.sha256(obs.canonical({'nonce':nonce,'lease':self.identity,'root':self.root_identity})).hexdigest()

    def verify(self):
        if file_key(self.fd) != self.identity or file_key(self.root_fd) != self.root_identity:
            fail('lease identity changed')
        # Do not reacquire a lost lock: inspect the actual kernel FLOCK record.
        if os.getppid()!=self.lock_owner_pid or obs.process(self.lock_owner_pid)[0]!=self.lock_owner_birth:
            fail('lease watchdog parent changed')
        st = os.fstat(self.fd)
        matches = 0
        for line in open('/proc/locks'):
            fields = line.split()
            if len(fields) < 8 or fields[1:4] != ['FLOCK','ADVISORY','WRITE']:
                continue
            try:
                owner = int(fields[4]); major,minor,inode = fields[5].split(':')
                same = (owner == self.lock_owner_pid and int(major,16) == os.major(st.st_dev) and
                        int(minor,16) == os.minor(st.st_dev) and int(inode) == st.st_ino)
            except (ValueError, IndexError):
                fail('invalid kernel lease record')
            if same: matches += 1
        if matches != 1: fail('exclusive supervisor lease not held')


class GraphProducer:
    """Actual observations and stable commitments, under already-owned custody.

    This class does not establish the external privileged-writer exclusion or
    target-namespace mount authority. A future reviewed operation owner must
    establish both before invoking it. Data is never a release by itself.
    """
    def __init__(self, custody, union, target_pid, hosts, owned_fds, boot_id, caps, latch):
        if type(latch) is not CustodyLatch:fail('operation latch required')
        if type(custody) is not source.ExactSourceCustody or custody.state != 'HELD': fail('actual frozen source custody required')
        if type(union) is not UnionChannel or union.state != 'HELD' or union.lease is not custody.lease: fail('actual union owner channel required')
        union.require_ready()
        if set(union.observed_targets) != {'/src/scripts','/out/build','/out/source/linux-6.12.0-211.44.1.el10_2','/work'}: fail('four independently observed owner outputs required')
        lease = custody.lease
        if type(lease) is not RootLease: fail('exact root lease required')
        if union.custody_sha != custody.custody_sha256: fail('union custody commitment differs')
        self.custody, self.union, self.latch = custody, union, latch
        if type(owned_fds) is not dict or set(owned_fds) != {'/src/scripts','/out/build','/out/source/linux-6.12.0-211.44.1.el10_2','/work'}:
            fail('four actual held owner descriptors required')
        self.lease, self.pid, self.hosts = lease, target_pid, dict(hosts)
        self.owned_fds = dict(owned_fds); self.expected = obs.process(target_pid)
        self.boot_id, self.caps = boot_id, dict(caps)
        self.state = 'PREPARING'; self.pre = None; self.data = None; self.output_epoch = None
        self.fd_pins = {k:file_key(v) for k,v in self.owned_fds.items()}
        self._validate_owned()
        output_roots={target:self.hosts[target] for target in self.owned_fds if target!='/work'}
        output_hashes={target:self.union.observed_targets[target]['inventory_sha256'] for target in output_roots}
        self.output_epoch=immutable_epoch.ImmutableEpoch.__new__(immutable_epoch.ImmutableEpoch)
        self.output_epoch.__init__(output_roots,output_hashes,self.caps['boot'])
        self._validate_owned()

    def _validate_owned(self):
        self.lease.verify(); self.custody.verify(); self.union.require_ready(); cap(self.caps, self.boot_id)
        if obs.process(self.pid) != self.expected: fail('target birth or mount namespace changed')
        for target, fd in self.owned_fds.items():
            s = os.fstat(fd)
            if not stat.S_ISDIR(s.st_mode) or file_key(fd) != self.fd_pins[target]: fail('owned directory changed')
            named,_ = obs.direct_path(self.hosts[target])
            if (named.st_dev,named.st_ino) != (s.st_dev,s.st_ino): fail('owned path substituted')
            if self.union.observed_targets[target]['identity'] != obs.ident(s): fail('owner output identity differs')
            if target == '/work': source.root_private(fd)
            elif self.output_epoch is None: source.walk(fd,self.hosts[target],'verify')
        if self.output_epoch is not None: self.output_epoch.verify()

    def observe_pre_shadow(self):
        if self.state != 'PREPARING': fail('pre-shadow state')
        token=self.latch.begin('SOURCES_HELD')
        self._validate_owned()
        self.pre, self.pre_boot_ns = obs.snapshot_before_children(self.pid, self.expected)
        parent = self.hosts['/src/kernel/rust']
        # Frozen source epoch already binds parent membership and bytes.
        self._validate_owned()
        self.latch.publish(token,lambda:setattr(self,'state','PRE_SHADOW_HELD'))
        return self.pre

    def observe_effective(self):
        if self.state != 'PRE_SHADOW_HELD': fail('pre-shadow missing')
        token=self.latch.begin('PRE_SHADOW_HELD')
        self._validate_owned()
        cache=dict(self.custody.epoch.contents);cache.update(self.output_epoch.contents)
        rows, view = obs.capture_graph(self.pid, self.expected, self.hosts, self.pre, cache)
        self._validate_owned()
        self.mounts, self.view = rows, view
        self.graph_sha256 = self._custody_hash(rows, view)
        self.custody_sha256 = self.custody.custody_sha256
        payload = dict(synthetic=False, contract_sha256=obs.CONTRACT_SHA,
                       custody=dict(owner='root-graph-supervisor',pid=os.getpid(),uid=os.geteuid(),
                                    nonce=self.lease.nonce,lease_sha256=self.lease.lease_sha256,
                                    custody_sha256=self.custody_sha256,
                                    exclusion='source-writers-excluded-and-work-exclusive'),
                       mounts=rows,pre_shadow=self.pre,effective_view=view)
        # Actual selected parser verifies ancestry/aliases/parent mount/157/view closure.
        parsed = adapter.parser()(obs.canonical(payload))
        if parsed.synthetic is not False or parsed.authority is not None: fail('candidate parser result')
        self.data = payload
        self.data_sha256 = hashlib.sha256(obs.canonical(payload)).hexdigest()
        self.latch.publish(token,lambda:setattr(self,'state','OBSERVED_NOT_RELEASED'))
        return payload

    def _custody_hash(self, rows, view):
        # Computed from real observed records and retained FD identities, not caller claims.
        return hashlib.sha256(obs.canonical(dict(lease=self.lease.lease_sha256,nonce=self.lease.nonce,
             target_pid=self.pid, target_identity=self.expected, fds=self.fd_pins,
             pre_shadow_sha256=self.pre['snapshot_sha256'], rows=rows, view=view))).hexdigest()

    def reobserve(self):
        if self.state != 'OBSERVED_NOT_RELEASED': fail('graph was not observed')
        try:
            self._validate_owned()
            cache=dict(self.custody.epoch.contents);cache.update(self.output_epoch.contents)
            rows, view = obs.capture_graph(self.pid, self.expected, self.hosts, self.pre, cache)
            self._validate_owned()
            if self._custody_hash(rows, view) != self.graph_sha256: fail('graph custody changed')
            return self.data
        except BaseException:
            self.state = 'UNKNOWN_RETAINED'
            raise


if __name__ == '__main__':
    raise RuntimeError('SOURCE ONLY: privileged-writer custody, root bootstrap, mount owner and one-shot execution admission are not established')
