"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only custody-channel adapter. This is not a build or execution release.
"""
import hashlib
import pidfd_compat
import deferred_fork
from pidfd_custody import PidfdCustodyRecord,SocketDupRecord,PublicationUnknown
import fcntl
import json
import math
import os
import secrets
import select
import socket
import stat
import struct
import sys
import time
import threading
import types
from pathlib import Path

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/RESTART-REPAIR-20261030/combined-graph-source-1')
SOURCE_SHA = '74eec517909d92d178d77771dd8ae59e826df50cd17121957a03e320b93d1c96'
CONTRACT_SHA = 'd4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd'
# Must be installed by the separately reviewed root owner; never configured by caller.
BOOTSTRAP = '/etc/mckernel/m14-graph-owner/bootstrap.json'
MAX_FRAME = 2 * 1024 * 1024
WIRE_PATH = Path(__file__).parent / 'custody_protocol_v2.py'
WIRE_SHA = '587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb'

def load_wire():
    raw = WIRE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != WIRE_SHA:
        raise ValueError('wire source mismatch')
    module = types.ModuleType('_m14_custody_wire')
    exec(compile(raw, str(WIRE_PATH), 'exec'), module.__dict__)
    return module


def fail(message):
    raise ValueError(message)


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            fail('duplicate JSON key')
        out[key] = value
    return out


def shape(d, keys):
    if type(d) is not dict or set(d) != set(keys.split()):
        fail('wrong record shape')


def digest(b):
    return hashlib.sha256(b).hexdigest()


def valid_sha(s):
    return type(s) is str and len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def trusted_file(path, limit=MAX_FRAME):
    """Open a root-owned non-writable path component by component, without symlinks."""
    if type(path) is not str or not path.startswith('/') or '//' in path:
        fail('non-absolute trusted path')
    parts = path.split('/')[1:]
    if not parts or any(p in ('', '.', '..') for p in parts):
        fail('invalid trusted path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for idx, part in enumerate(parts):
            st = os.fstat(fd)
            if st.st_uid != 0 or st.st_mode & 0o022 or not stat.S_ISDIR(st.st_mode):
                fail('untrusted path parent')
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
            if idx < len(parts) - 1:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 or st.st_nlink != 1 or st.st_size > limit:
            fail('untrusted root file')
        flags = bytearray(4)
        fcntl.ioctl(fd, 0x80086601, flags, True)
        if not struct.unpack('I', flags)[0] & 0x10:
            fail('trusted root file is not immutable')
        out = b''
        while len(out) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(out)))
            if not chunk:
                break
            out += chunk
        end = os.fstat(fd)
        if len(out) > limit or (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (end.st_dev, end.st_ino, end.st_size, end.st_mtime_ns, end.st_ctime_ns):
            fail('root file changed')
        return out
    finally:
        os.close(fd)


def proc_identity(pid):
    text = Path('/proc/%d/stat' % pid).read_text()
    fields = text.rsplit(')', 1)[1].split()
    if len(fields) < 20 or fields[0] in ('Z', 'X', 'x'):
        fail('process identity unavailable')
    return (int(fields[1]), fields[19])


def parser():
    raw = (BASE / 'candidate_data.py').read_bytes()
    if digest(raw) != SOURCE_SHA:
        fail('parser source changed')
    module = types.ModuleType('_m14_pinned_candidate_data')
    module.__file__ = str(BASE / 'candidate_data.py')
    sys.modules[module.__name__] = module
    try:
        exec(compile(raw, module.__file__, 'exec'), module.__dict__)
        if digest(module.CONTRACT_BYTES) != CONTRACT_SHA or module.CONTRACT_SHA256 != CONTRACT_SHA:
            fail('contract changed')
        return module.parse_candidate_data
    finally:
        sys.modules.pop(module.__name__, None)


def clock_values():
    return time.time(), time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic()


def check_caps(caps, boot_id, times):
    shape(caps, 'utc boot mono boot_id')
    if (caps['boot_id'] != boot_id or boot_id != '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' or
        any(type(caps[k]) not in (int, float) or not math.isfinite(caps[k]) for k in ('utc', 'boot', 'mono')) or
        caps['utc'] > 1793774133 or caps['boot'] > 1571567.6959065471 or caps['mono'] > 1556229.568859425):
        fail('wrong boot or expanded UTC cap')
    for name, now in zip(('utc', 'boot', 'mono'), times):
        value = caps[name]
        if type(value) not in (float, int) or not math.isfinite(value) or not now < value:
            fail('expired or invalid clock cap')


class CustodySession:
    """Consumes an inherited root-supervisor socket and keeps it open until closed.

    A successful result authenticates a supervisor statement at a bounded instant;
    it is not permission to launch or proof of custody after this channel ends.
    """
    def __init__(self, fd, pidfd_record, owner):
        # All session construction/progression uses operation -> session -> record.
        with owner.lock:
            if type(pidfd_record) is not PidfdCustodyRecord or pidfd_record.state!='REGISTERED':
                fail('caller-owned pre-registered pidfd custody required')
            if (getattr(owner,'session',None) is not self or getattr(owner,'record',None) is not pidfd_record or
                type(getattr(owner,'duplicate',None)) is not SocketDupRecord or owner.state!='REGISTERED'):
                fail('pre-owned live operation and duplicate record required')
            self.pidfd_record=pidfd_record;self.owner=owner;self.duplicate=owner.duplicate
            self.closed=False;self.close_state='OPEN';self.sock=None;self.session_lock=threading.RLock()
            with self.session_lock:
                self._initialize(fd,pidfd_record,owner)

    def _require_owner_live(self,before_pidfd=False):
        if (self.owner.state!='REGISTERED' or self.owner.session is not self or
            self.owner.record is not self.pidfd_record or self.owner.duplicate is not self.duplicate or
            self.close_state!='OPEN'):
            fail('operation or session is no longer live')
        if before_pidfd:
            if self.pidfd_record.state!='REGISTERED' or self.duplicate.state not in ('REGISTERED','ADOPTED'):
                fail('constructor custody changed')
        elif self.pidfd_record.state!='VERIFIED_HELD' or self.duplicate.state!='ADOPTED':
            fail('session custody changed')

    def _initialize(self,fd,pidfd_record,owner):
        self._require_owner_live(before_pidfd=True)
        with deferred_fork.DeferredFork() as guard:
            self._require_owner_live(before_pidfd=True)
            self.sock=guard.duplicate_and_adopt(self.duplicate,fd)
        self._require_owner_live(before_pidfd=True)
        self.wire = load_wire()
        try:
            if self.sock.family != socket.AF_UNIX or self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_STREAM:
                fail('wrong channel type')
            pid, uid, gid = struct.unpack('3i', self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != 0 or pid != os.getppid():
                fail('peer is not root supervisor parent')
            self.pid, self.uid, self.gid = pid, uid, gid
            self.parent, self.birth = proc_identity(pid)
            with deferred_fork.DeferredFork() as guard:
                self._require_owner_live(before_pidfd=True)
                self.pidfd = guard.acquire_and_pin(pidfd_record,pid,self.birth)
            self._require_owner_live()
            self.bootstrap = json.loads(trusted_file(BOOTSTRAP), object_pairs_hook=unique)
            shape(self.bootstrap, 'version supervisor_source supervisor_sha256 interpreter_sha256 argv contract_sha256 lease_sha256 custody_sha256 nonce caps boot_id max_age_seconds max_step_seconds')
            b = self.bootstrap
            if b['version'] != 1 or b['contract_sha256'] != CONTRACT_SHA or not all(valid_sha(b[k]) for k in ('supervisor_sha256', 'interpreter_sha256', 'lease_sha256', 'custody_sha256', 'nonce')):
                fail('bootstrap source or contract')
            if digest(trusted_file(b['supervisor_source'])) != b['supervisor_sha256']:
                fail('supervisor source mismatch')
            if type(b['argv']) is not list or not b['argv'] or b['supervisor_source'] not in b['argv'] or not all(type(x) is str and x for x in b['argv']):
                fail('supervisor argv binding')
            argv = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
            if argv[-1:] != [b''] or [x.decode('utf-8') for x in argv[:-1]] != b['argv']:
                fail('supervisor argv changed')
            with open('/proc/%d/exe' % pid, 'rb') as exe:
                if digest(exe.read()) != b['interpreter_sha256']:
                    fail('supervisor executable changed')
            self.boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            age = b['max_age_seconds']
            if type(age) not in (int, float) or not math.isfinite(age) or not 0 < age <= 30 or b['boot_id'] != self.boot_id:
                fail('bootstrap freshness or boot')
            self.max_age = age
            step=b['max_step_seconds']
            if type(step) not in (int,float) or not math.isfinite(step) or not 0 < step <= 600:
                fail('reviewed finite operation limit required')
            self.max_step=step
            check_caps(b['caps'], self.boot_id, clock_values())
            self.operation_nonce = b['nonce']
            self.challenge = secrets.token_hex(32)
            self.sequence = 1
            request_boot = clock_values()[1]
            self.local_birth = proc_identity(os.getpid())[1]
            deadline = min(b['caps']['boot'], request_boot + self.max_step)
            request = dict(challenge=self.challenge, consumer_pid=os.getpid(), consumer_birth=self.local_birth,
                           boot_id=self.boot_id, contract_sha256=CONTRACT_SHA)
            self.wire.send(self.sock, self.wire.envelope('graph','graph-observe-v1',self.operation_nonce,
                           self.sequence,b['lease_sha256'],b['custody_sha256'],request), deadline)
            reply = self.wire.validate(self.wire.receive(self.sock, deadline), 'graph','graph-observe-v1',
                            self.operation_nonce,self.sequence,b['lease_sha256'],b['custody_sha256'])
            shape(reply, 'type nonce boot_id provider_pid provider_birth consumer_pid consumer_birth lease_sha256 observed_boot expires_boot custody_sha256 candidate')
            now = clock_values()
            check_caps(b['caps'], self.boot_id, now)
            if (reply['type'] != 'graph-observation-v1' or reply['nonce'] != self.challenge or
                reply['boot_id'] != self.boot_id or reply['provider_pid'] != pid or reply['provider_birth'] != self.birth or
                reply['consumer_pid'] != os.getpid() or reply['consumer_birth'] != self.local_birth or
                reply['lease_sha256'] != b['lease_sha256'] or reply['custody_sha256'] != b['custody_sha256']):
                fail('channel binding differs')
            observed, expires = reply['observed_boot'], reply['expires_boot']
            if (type(observed) not in (int, float) or type(expires) not in (int, float) or
                not math.isfinite(observed) or not math.isfinite(expires) or
                not request_boot <= observed <= now[1] or now[1] - observed > age or not now[1] < expires <= observed + age or
                expires > b['caps']['boot']):
                fail('stale or invalid observation')
            if type(reply['candidate']) is not dict:
                fail('candidate record missing')
            raw = json.dumps(reply['candidate'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            data = parser()(raw)
            if (data.synthetic is not False or data.pid != pid or data.uid != uid or data.nonce != self.operation_nonce or
                data.lease_sha256 != b['lease_sha256'] or data.custody_sha256 != reply['custody_sha256']):
                fail('candidate custody differs')
            if self._pid_exited() or proc_identity(pid) != (self.parent, self.birth):
                fail('supervisor identity changed')
            self._require_owner_live()
            self.data, self.expires_boot = data, expires
            self.candidate_sha256, self.custody_sha256 = digest(raw), reply['custody_sha256']
            self._require_owner_live()
        except BaseException:
            # Caller owns disposition; no constructor-side disposal.
            raise

    def _pid_exited(self):
        poll = select.poll()
        poll.register(self.pidfd, select.POLLIN)
        return bool(poll.poll(0))

    def revalidate(self):
        """Require a new same-channel custody assertion immediately before use."""
        # Failure transfers to the pre-registered caller-owned operation.
        with self.owner.lock:
            with self.session_lock:
                self._require_owner_live()
                data=self._revalidate()
                self._require_owner_live()
                return data

    def _revalidate(self):
        if self.closed:
            fail('custody session closed')
        now = clock_values()
        check_caps(self.bootstrap['caps'], self.boot_id, now)
        if now[1] >= self.expires_boot or self._pid_exited() or proc_identity(self.pid) != (self.parent, self.birth):
            fail('custody expired or supervisor changed')
        token = secrets.token_hex(32)
        request_boot = now[1]
        self.sequence += 1
        deadline = min(self.bootstrap['caps']['boot'], self.expires_boot, request_boot + self.max_step)
        request = dict(type='graph-revalidate-v1', nonce=token, original_nonce=self.challenge,
                       candidate_sha256=self.candidate_sha256, lease_sha256=self.bootstrap['lease_sha256'],
                       custody_sha256=self.custody_sha256)
        self.wire.send(self.sock,self.wire.envelope('graph','graph-revalidate-v1',self.operation_nonce,
                       self.sequence,self.bootstrap['lease_sha256'],self.custody_sha256,request),deadline)
        result = self.wire.validate(self.wire.receive(self.sock,deadline),'graph','graph-revalidate-v1',
                       self.operation_nonce,self.sequence,self.bootstrap['lease_sha256'],self.custody_sha256)
        shape(result, 'type nonce original_nonce candidate_sha256 lease_sha256 custody_sha256 observed_boot expires_boot')
        now = clock_values()
        check_caps(self.bootstrap['caps'], self.boot_id, now)
        t, end = result['observed_boot'], result['expires_boot']
        if (result['type'] != 'graph-custody-held-v1' or result['nonce'] != token or
            result['original_nonce'] != self.challenge or result['candidate_sha256'] != self.candidate_sha256 or
            result['lease_sha256'] != self.bootstrap['lease_sha256'] or result['custody_sha256'] != self.custody_sha256 or
            type(t) not in (int, float) or type(end) not in (int, float) or not math.isfinite(t) or not math.isfinite(end) or
            not request_boot <= t <= now[1] or now[1] - t > self.max_age or now[1] >= self.expires_boot or not now[1] < end <= t + self.max_age or
            end > self.bootstrap['caps']['boot'] or self._pid_exited() or proc_identity(self.pid) != (self.parent, self.birth)):
            fail('custody revalidation rejected')
        self._require_owner_live()
        self.expires_boot = end
        self._require_owner_live()
        return self.data

    def close(self,owner):
        # Lock order is operation -> session -> pidfd -> socket record.
        with owner.lock:
            with self.session_lock:
                if (owner is not self.owner or getattr(owner,'session',None) is not self or
                    getattr(owner,'record',None) is not self.pidfd_record or owner.duplicate is not self.duplicate or
                    owner.state=='UNKNOWN_RETAINED'):
                    raise RuntimeError('caller-owned disposition required')
                if self.close_state!='OPEN':raise RuntimeError('close already attempted or unavailable')
                self.close_state='CLOSING'
                try:
                    with deferred_fork.DeferredFork() as guard:
                        guard.close_session(self.pidfd_record,self.duplicate)
                except BaseException:
                    self.close_state='CLOSURE_UNKNOWN'
                    if self.pidfd_record.state in ('VERIFIED_HELD','CLOSING','VERIFIED_CLOSED'):
                        try:self.pidfd_record.closure_unknown()
                        except BaseException as error:self.close_publication_error=error
                    if self.duplicate.state in ('DUPLICATED','ADOPTED','CLOSING'):
                        try:self.duplicate.closure_unknown()
                        except BaseException as error:self.socket_publication_error=error
                    raise
                if (self.pidfd_record.state!='VERIFIED_CLOSED' or self.duplicate.state!='VERIFIED_CLOSED'):
                    self.close_state='CLOSURE_UNKNOWN'
                    raise RuntimeError('close disposition unavailable')
                # Reentrant configured-stop handlers may latch UNKNOWN while
                # restoring the mask. Keep the confirmed dispositions, never
                # restore live status, and propagate the owner failure.
                self.closed=True;self.close_state='VERIFIED_CLOSED'
                if owner.state=='UNKNOWN_RETAINED':raise RuntimeError('operation failed after local close')
