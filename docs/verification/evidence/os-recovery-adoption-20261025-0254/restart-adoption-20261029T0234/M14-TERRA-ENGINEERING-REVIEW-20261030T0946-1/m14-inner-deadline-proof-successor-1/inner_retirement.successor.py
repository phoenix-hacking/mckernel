"""Tool-only derivative; no execution authority without a new exact release.

Uses the frozen tool_owner.run and host Docker retirement methods. Only the
Docker.call spawn/wait body is derived, to retain identities before first wait.
The outer process also directly joins the actual tool owner. Workload status and
physical retirement remain independent. Never removes a container or lease.
"""
from pathlib import Path
import argparse
import ctypes
import errno
import hashlib
import importlib.util
import json
import math
import os
import resource
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
OWNER = Path('/home/holden/mckernel-work/scratch/native-host-objtool-driver-20261018-1/tool_owner.py')
OWNER_SHA = '194f4ac133fa8e4aea1e47eea0e13f8757e70f195e629788b9dcb78d6fb5a1cf'
MAX_PROC = 4096
MAX_SNAPSHOTS = 128
MAX_PROOF_BYTES = 4 << 20
MAX_COMMANDS = 12
MAX_KNOWN = 512
MAX_CAPTURE_BYTES = 8 << 20
MAX_ALL_CAPTURE_BYTES = 64 << 20
PRODUCER_PROFILE = dict(cpus=[0], address_space_bytes=1 << 30, cpu_seconds=30,
                        file_bytes=8 << 20, outer_wall_seconds=600, jobs=1)
SCHEMA = 'mckernel.process-retirement.v2'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def resources():
    return dict(cpus=sorted(os.sched_getaffinity(0)),
                rlimit_as=list(resource.getrlimit(resource.RLIMIT_AS)),
                rlimit_cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                rlimit_fsize=list(resource.getrlimit(resource.RLIMIT_FSIZE)),
                rlimit_nproc=list(resource.getrlimit(resource.RLIMIT_NPROC)))


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def row(pid, raw):
    fields = raw.rsplit(')', 1)[1].split()
    return dict(pid=int(pid), starttime=fields[19], ppid=int(fields[1]),
                pgrp=int(fields[2]), session=int(fields[3]), state=fields[0], raw_stat=raw)


def identity(value):
    return {key: value[key] for key in ('pid', 'starttime', 'pgrp', 'session')}


def current_identity(pid):
    return identity(row(pid, Path('/proc', str(pid), 'stat').read_text()))


def subreaper_state():
    value = ctypes.c_int(-1)
    libc = ctypes.CDLL(None, use_errno=True)
    code = libc.prctl(37, ctypes.byref(value), 0, 0, 0)
    return dict(get_rc=code, value=value.value)


def enable_subreaper():
    """Dedicated owner/outer processes retain orphaned descendants until joined.

    Never reap an unknown child. Such children block proof and all next commands.
    This is called before any owned Popen, not retrofitted after a client exits.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'subreaper SET failed')
    require(subreaper_state() == dict(get_rc=0, value=1), 'subreaper GET failed')
    require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, 'SIGCHLD must retain waitable children')
    require(len(list(Path('/proc/self/task').iterdir())) == 1, 'single dedicated owner task required')


def containment_observation():
    tasks = []
    for task in sorted(Path('/proc/self/task').iterdir(), key=lambda item: int(item.name)):
        with (task / 'children').open() as stream:
            raw = stream.read(32769)
        require(len(raw) <= 32768, 'child identity bound exceeded')
        tasks.append(dict(tid=int(task.name), raw_children=raw))
    try:
        result = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError as exc:
        wait = dict(state='ECHILD', errno=exc.errno)
    else:
        wait = dict(state='LIVE_CHILDREN') if result is None else dict(
            state='WAITABLE_CHILD', si_pid=result.si_pid, si_uid=result.si_uid,
            si_signo=result.si_signo, si_status=result.si_status, si_code=result.si_code)
    return dict(boot_id=boot_id(), observer=current_identity(os.getpid()),
                monotonic_ns=time.monotonic_ns(), subreaper=subreaper_state(),
                sigchld=int(signal.getsignal(signal.SIGCHLD)), tasks=tasks, waitid=wait)


def validate_closure(observation, anchor, boot):
    require(observation['boot_id'] == boot and observation['observer'] == anchor,
            'containment observer identity/boot changed')
    require(observation['subreaper'] == dict(get_rc=0, value=1) and
            type(observation['subreaper']['get_rc']) is int and
            type(observation['subreaper']['value']) is int, 'subreaper state unproven')
    require(type(observation['sigchld']) is int and observation['sigchld'] == 0,
            'SIGCHLD does not retain children')
    tasks = observation['tasks']
    require(len(tasks) == 1 and tasks[0]['tid'] == anchor['pid'] and
            isinstance(tasks[0]['raw_children'], str) and not tasks[0]['raw_children'].strip(),
            'unknown/live/adopted child or extra observer task')
    require(observation['waitid'] == dict(state='ECHILD', errno=errno.ECHILD),
            'kernel child closure unproven')
    require(type(observation['monotonic_ns']) is int and observation['monotonic_ns'] > 0,
            'containment observation order missing')


def prepare_launch():
    observation = containment_observation()
    validate_closure(observation, observation['observer'], observation['boot_id'])
    return observation


def census():
    """A bounded raw process census; denied/malformed reads retain uncertainty."""
    result = dict(boot_id=boot_id(), rows=[], errors=[], observer_uid=os.getuid(),
                  proc_mountinfo=[line for line in Path('/proc/self/mountinfo').read_text().splitlines()
                                  if ' - proc ' in line])
    if not result['proc_mountinfo'] or any('hidepid=' in line and 'hidepid=0' not in line
                                          for line in result['proc_mountinfo']):
        result['errors'].append('proc visibility unproven')
    entries = sorted(Path('/proc').glob('[0-9]*/stat'), key=lambda p: int(p.parent.name))
    if len(entries) > MAX_PROC:
        result['errors'].append('process census exceeds bound')
        return result
    for path in entries:
        try:
            result['rows'].append(row(path.parent.name, path.read_text()))
        except FileNotFoundError:
            # Unrelated processes may exit during enumeration. A tracked process
            # still needs its stable identity or terminal absence in final census.
            continue
        except (OSError, ValueError, IndexError) as exc:
            result['errors'].append({'pid': int(path.parent.name), 'error': type(exc).__name__})
    return result


def derive_members(snapshot, root, anchor=None):
    rows = {item['pid']: item for item in snapshot['rows']}
    tree = {root['pid']} if root['pid'] in rows else set()
    if anchor is not None:
        tree.update(pid for pid, item in rows.items() if item['ppid'] == anchor['pid'])
    changed = True
    while changed:
        children = {pid for pid, item in rows.items() if item['ppid'] in tree}
        changed = not children.issubset(tree)
        tree.update(children)
    return sorted(tree), sorted(pid for pid, item in rows.items() if item['pgrp'] == root['pgrp'])


def validate_proof(proof):
    """Pure shared predicate over raw producer output, never PID absence alone."""
    require(proof.get('schema') == SCHEMA, 'proof schema')
    require(proof.get('uncertainties') == [] and proof.get('forced') is False, 'uncertain/forced retirement')
    first, final = proof['snapshots'][0], proof['snapshots'][-1]
    require(first['phase'] == 'pre_wait' and final['phase'] == 'post_wait', 'missing pre/post wait')
    require(proof['direct_wait'].get('joined') is True and type(proof['direct_wait'].get('exit_code')) is int,
            'missing direct join')
    require(not proof['privileged_wrapper'] or proof['direct_wait']['exit_code'] >= 0, 'signalled privileged wrapper')
    root = proof['identity']
    containment = proof['containment']
    require(containment['schema'] == 'mckernel.subreaper-closure.v1', 'containment schema')
    before = containment['pre_launch']
    anchor = before['observer']
    require(root['pid'] != anchor['pid'], 'observer cannot be client')
    observations = [before, *containment['post_join']]
    require(len(observations) == 3, 'two final containment observations required')
    for obs in observations:
        validate_closure(obs, anchor, proof['boot_id'])
    require(observations[0]['monotonic_ns'] < observations[1]['monotonic_ns'] < observations[2]['monotonic_ns'],
            'containment observation order differs')
    known = {item['pid']: item for item in proof['known_identities']}
    require(known.get(root['pid']) == root, 'missing known owner identity')
    initial = {item['pid']: item for item in first['rows']}
    require(root['pid'] in initial and identity(initial[root['pid']]) == root, 'initial identity mismatch')
    for snap in proof['snapshots']:
        require(snap.get('errors') == [] and snap['boot_id'] == proof['boot_id'], 'census uncertain/boot changed')
        require(snap.get('observer_uid') == 1000, 'wrong or missing observer UID')
        mounts = snap.get('proc_mountinfo', [])
        require(mounts and any(line.split()[4] == '/proc' and ' - proc ' in line for line in mounts),
                'missing full proc mount observation')
        require(not any('hidepid=' in line and 'hidepid=0' not in line for line in mounts),
                'hidden proc visibility')
        require(any(item['pid'] == 1 for item in snap['rows']), 'incomplete proc census')
        require(any(item['pid'] == anchor['pid'] and identity(item) == anchor for item in snap['rows']),
                'containment anchor missing or reused in census')
        tree, group = derive_members(snap, root, anchor)
        require(snap['tree'] == tree and snap['group'] == group, 'raw membership differs')
        for item in snap['rows']:
            require(row(item['pid'], item['raw_stat']) == item, 'raw stat mismatch')
            if item['pid'] in known:
                require(identity(item) == known[item['pid']], 'known identity reused or changed')
        require(all(pid in known for pid in tree + group), 'untracked tree/group member')
    require(len([snap for snap in proof['snapshots'] if snap['phase'] == 'post_wait']) >= 2,
            'two terminal censuses required')
    require(any(item['pid'] == 1 for item in final['rows']), 'namespace-visible PID 1 required; host identity not inferred')
    require(final['group'] == [] and final['tree'] == [], 'live process tree/group')
    groups = {item['pgrp'] for item in known.values()}
    sessions = {item['session'] for item in known.values()}
    for snap in proof['snapshots'][-2:]:
        require(snap['phase'] == 'post_wait', 'consecutive final censuses required')
        require(not any(item['pid'] in known or item['ppid'] in known or
                        item['pgrp'] in groups or item['session'] in sessions
                        for item in snap['rows']), 'tracked descendant/group/session survives')
    require(not any(item['pid'] in known for item in final['rows']), 'known identity still present')
    return True


class ProcessProof:
    def __init__(self, process, privileged_wrapper=False, pre_launch=None):
        self.process = process
        self.data = dict(schema=SCHEMA, boot_id=boot_id(), identity=None, known_identities=[],
                         snapshots=[], direct_wait=dict(joined=False, exit_code=None), forced=False,
                         privileged_wrapper=privileged_wrapper, uncertainties=[], retirement_proven=False,
                         observer_resources=resources(), containment=dict(schema='mckernel.subreaper-closure.v1',
                         pre_launch=pre_launch, post_join=[]))
        self.known = {}
        self.proof_bytes = 0
        if pre_launch is None:
            self.uncertain('missing prelaunch containment')
        # Popen has returned, but poll/wait have NOT reaped even a fast child.
        try:
            self.data['identity'] = current_identity(process.pid)
            self.observe('pre_wait')
        except (OSError, ValueError, IndexError) as exc:
            self.uncertain('initial identity unavailable: ' + type(exc).__name__)

    def uncertain(self, message):
        message = message[:256]
        if message not in self.data['uncertainties'] and len(self.data['uncertainties']) < 32:
            self.data['uncertainties'].append(message)

    def observe(self, phase):
        if self.data['identity'] is None:
            return
        try:
            snap = census()
        except (OSError, ValueError, IndexError) as exc:
            self.uncertain('census failed: ' + type(exc).__name__)
            return
        snap['phase'] = phase
        before = self.data['containment']['pre_launch']
        anchor = before['observer'] if before is not None else None
        snap['tree'], snap['group'] = derive_members(snap, self.data['identity'], anchor)
        selected = set(snap['tree'] + snap['group'])
        changed = False
        for item in snap['rows']:
            if item['pid'] in selected:
                value = identity(item)
                previous = self.known.get(item['pid'])
                if previous is not None and previous != value:
                    self.uncertain('tracked identity changed')
                elif previous is None:
                    if len(self.known) >= MAX_KNOWN:
                        self.uncertain('known identity bound exceeded')
                    else:
                        self.known[item['pid']] = value
                        changed = True
        # Keep every identity discovery and raw pre/post snapshots; unchanged
        # intermediate censuses add no new proof and do not grow evidence forever.
        if phase != 'waiting' or changed or snap['errors']:
            if len(self.data['snapshots']) >= MAX_SNAPSHOTS:
                self.uncertain('snapshot bound exceeded')
            else:
                snap_bytes = len(json.dumps(snap).encode())
                if self.proof_bytes + snap_bytes > MAX_PROOF_BYTES - (256 << 10):
                    self.uncertain('proof exceeds evidence bound; ownership retained')
                else:
                    self.data['snapshots'].append(snap)
                    self.proof_bytes += snap_bytes
        self.data['known_identities'] = sorted(self.known.values(), key=lambda x: x['pid'])

    def joined(self, code):
        self.data['direct_wait'] = dict(joined=True, exit_code=code)
        for _ in range(2):
            self.observe('post_wait')
            try:
                self.data['containment']['post_join'].append(containment_observation())
            except (OSError, ValueError, IndexError) as exc:
                self.uncertain('containment observation failed: ' + type(exc).__name__)
            time.sleep(0.01)
        try:
            validate_proof(self.data)
            self.data['retirement_proven'] = True
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            self.data['retirement_proven'] = False
            self.uncertain(str(exc))
        return self.data


# Private source-only adaptation. The host review of the predecessor is not an
# execution release for this module. A separately reviewed and authenticated
# host-to-CID/namespace transport is deliberately not supplied here.
INNER_OPERATION = 'M14_INNER_CONFIGURE_QUIESCENCE_SOURCE_ONLY'
INNER_DISABLED = True
HOST_EXCHANGE = None

def _is_sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

def _inner_source_sha256():
    path=Path(__file__);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);require(before.st_size<=2*1024*1024,'observer source too large')
        digest=hashlib.sha256();count=0
        while True:
            part=os.read(fd,65536)
            if not part:break
            count+=len(part);require(count<=2*1024*1024,'observer source grew');digest.update(part)
        after=os.fstat(fd);named=os.lstat(path)
        attrs=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        require(count==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in attrs),'observer source changed')
        return digest.hexdigest()
    finally:os.close(fd)

# Live values and their external authenticated issuer remain absent in this source.
# The fixed UTC is an upper bound, not a release or a fresh operational clock.
MAX_UTC=1793774133.0

def _positive_finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0

def _check_deadlines(binding, requested=None):
    caps=binding.get('deadline_caps')
    require(isinstance(caps,dict) and set(caps)=={'utc','boot','monotonic'} and all(_positive_finite(x) for x in caps.values()), 'deadline caps unbound or nonfinite')
    require(caps['utc']<=MAX_UTC, 'UTC cutoff widened')
    if requested is not None:
        require(_positive_finite(requested) and requested<=caps['monotonic'], 'requested deadline outside monotonic cap')
    utc=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
    require(all(_positive_finite(x) for x in (utc,boot,mono)) and utc<caps['utc'] and boot<caps['boot'] and mono<caps['monotonic'], 'deadline elapsed or clock unknown')
    if requested is not None:require(mono<requested,'requested deadline elapsed')

def _inner_require_binding(binding, fds):
    require(isinstance(binding,dict) and set(binding)=={'operation','cid','nonce','profile_sha256','driver_sha256','observer_sha256','host_authority_sha256','caps_authority_sha256','deadline_caps','boot_id','self_identity','views'}, 'inner binding shape')
    require(binding['operation']==INNER_OPERATION and _is_sha(binding['cid']) and _is_sha(binding['profile_sha256']) and _is_sha(binding['driver_sha256']) and _is_sha(binding['observer_sha256']) and _is_sha(binding['host_authority_sha256']) and _is_sha(binding['caps_authority_sha256']), 'inner operation/hash binding')
    require(_inner_source_sha256()==binding['observer_sha256'], 'observer source binding differs')
    require(isinstance(binding['nonce'],str) and len(binding['nonce'])==32 and all(c in '0123456789abcdef' for c in binding['nonce']), 'inner nonce')
    require(isinstance(binding['views'],dict) and set(binding['views'])=={'pid','mount','proc'}, 'inner views')
    require(isinstance(fds,dict) and set(fds)=={'pid','mount','proc'} and all(type(x) is int and x>=0 for x in fds.values()) and len(set(fds.values()))==3, 'pre-bound handles')
    for name,path in (('pid','/proc/self/ns/pid'),('mount','/proc/self/ns/mnt'),('proc','/proc')):
        expected=binding['views'][name]
        require(isinstance(expected,list) and len(expected)==2 and all(type(x) is int and x>0 for x in expected), 'view identity')
        descriptor=os.fstat(fds[name]); current=os.stat(path)
        require([descriptor.st_dev,descriptor.st_ino]==expected==[current.st_dev,current.st_ino], 'view changed: '+name)
    require(boot_id()==binding['boot_id'] and current_identity(os.getpid())==binding['self_identity'], 'inner self/boot changed')

def _canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def _host_exchange(phase, payload):
    require(HOST_EXCHANGE is not None, 'authenticated external host exchange unbound')
    original=_canonical_json(payload)
    sent=json.loads(original)
    reply=HOST_EXCHANGE(phase,sent)
    # The transport gets a detached copy. Check both copies after the callback:
    # mutation and an aliased, identically mutated reply never make an ACK valid.
    require(_canonical_json(payload)==original and _canonical_json(sent)==original, 'host callback mutated payload')
    require(isinstance(reply,dict) and set(reply)=={'phase','payload','decision','authority_sha256'}, 'host ack shape')
    require(reply['phase']==phase and _canonical_json(reply['payload'])==original and reply['decision']=='ACK' and _is_sha(reply['authority_sha256']), 'host ack mismatch')
    return reply

class InnerConfigureOwner:
    """Only exact configure child; no generic observer or lease-release authority."""
    def __init__(self,binding,fds):
        self.binding=json.loads(json.dumps(binding,sort_keys=True,allow_nan=False));self.fds=dict(fds);self.process=None;self.proof=None;self.pre=None;self.state='NEW';self.error=None
    def _fail_unknown(self,exc):
        self.state='UNKNOWN';self.error=type(exc).__name__+': '+str(exc)
    def launch(self,argv,cwd,env,stdout,stderr):
        require(INNER_DISABLED is False, 'SOURCE_ONLY: inner launch disabled')
        require(self.state=='NEW', 'single use/UNKNOWN owner')
        require(HOST_EXCHANGE is not None, 'authenticated external host exchange unbound')
        try:
            _check_deadlines(self.binding)
            _inner_require_binding(self.binding,self.fds)
            enable_subreaper()
            self.pre=prepare_launch()
            require(self.pre['observer']==self.binding['self_identity'] and self.pre['boot_id']==self.binding['boot_id'], 'prelaunch owner differs')
            require(isinstance(argv,list) and argv and all(isinstance(x,str) and x and '\0' not in x for x in argv), 'argv')
            argv=list(argv);env=dict(env)
            ready={'binding':self.binding,'pre_launch':self.pre,'argv':argv,'cwd':cwd,'env_sha256':hashlib.sha256(json.dumps(env,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()}
            ready_digest=hashlib.sha256(json.dumps(ready,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            self.ready_ack=_host_exchange('READY',ready)
            _check_deadlines(self.binding)
            require(self.ready_ack['authority_sha256']==self.binding['host_authority_sha256'], 'host authority differs')
            require(hashlib.sha256(json.dumps(ready,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==ready_digest, 'ready changed')
            self.ready_digest=ready_digest
            self.binding_digest=hashlib.sha256(json.dumps(self.binding,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            _inner_require_binding(self.binding,self.fds)
            pre2=prepare_launch()
            require(pre2['observer']==self.pre['observer'] and pre2['boot_id']==self.pre['boot_id'] and pre2['monotonic_ns']>self.pre['monotonic_ns'], 'pre-spawn closure drift')
            _check_deadlines(self.binding)
            self.state='SPAWN_ATTEMPTED'
            self.process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            self.proof=ProcessProof(self.process,privileged_wrapper=False,pre_launch=pre2)
            require(self.proof.data.get('identity') is not None and self.proof.data['identity'].get('pid')==self.process.pid and not self.proof.data['uncertainties'], 'direct child identity unavailable')
            self.state='RUNNING'
        except BaseException as exc:
            self._fail_unknown(exc);raise
    def wait(self,absolute_deadline):
        require(INNER_DISABLED is False, 'SOURCE_ONLY: inner wait disabled')
        require(self.state=='RUNNING' and self.process is not None and self.proof is not None, 'not running/UNKNOWN owner')
        try:
            _check_deadlines(self.binding,absolute_deadline)
            while True:
                _check_deadlines(self.binding,absolute_deadline)
                left=absolute_deadline-time.monotonic()
                require(left>0,'deadline exhausted; retain ownership')
                self.proof.observe('waiting')
                require(not self.proof.data['uncertainties'],'census uncertainty')
                try:code=self.process.wait(timeout=min(0.1,left));break
                except subprocess.TimeoutExpired:continue
            require(type(code) is int,'direct wait status missing')
            _check_deadlines(self.binding,absolute_deadline)
            proof=self.proof.joined(code)
            require(proof.get('retirement_proven') is True,'descendant closure unknown')
            validate_proof(proof)
            require(proof['identity']['pid']==self.process.pid and proof['boot_id']==self.binding['boot_id'] and proof['containment']['pre_launch']['observer']==self.binding['self_identity'] and proof['direct_wait']['exit_code']==code, 'proof owner/wait mismatch')
            _inner_require_binding(self.binding,self.fds)
            require(hashlib.sha256(json.dumps(self.binding,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==self.binding_digest,'binding changed')
            _check_deadlines(self.binding,absolute_deadline)
            # The untrusted inner receipt cannot authorize its own acceptance.
            # External host channel must authenticate CID, namespace, sender,
            # owner and this exact canonical digest before a caller may continue.
            encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            require(len(encoded)<=MAX_PROOF_BYTES,'proof exceeds transport bound')
            receipt={'binding':self.binding,'ready_sha256':self.ready_digest,'proof_sha256':hashlib.sha256(encoded).hexdigest(),'proof':proof,'exit_code':code}
            self.final_ack=_host_exchange('PROOF',receipt)
            require(hashlib.sha256(_canonical_json(proof)).hexdigest()==receipt['proof_sha256'], 'proof changed during host ACK')
            require(hashlib.sha256(_canonical_json(self.binding)).hexdigest()==self.binding_digest, 'binding changed during host ACK')
            require(self.final_ack['authority_sha256']==self.ready_ack['authority_sha256'], 'host authority changed')
            _check_deadlines(self.binding,absolute_deadline)
            self.state='PROOF_ACKED_SOURCE_ONLY'
            return proof
        except BaseException as exc:
            self._fail_unknown(exc);raise
