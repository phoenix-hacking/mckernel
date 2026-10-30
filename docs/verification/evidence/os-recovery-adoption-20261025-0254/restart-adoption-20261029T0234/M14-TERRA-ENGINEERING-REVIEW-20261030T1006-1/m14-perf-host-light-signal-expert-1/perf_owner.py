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
    require(any(item['pid'] == 1 for item in final['rows']), 'full host proc census required')
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


import math
# Disabled two-phase perf source successor; no generic dispatch or CLI.
PERF_LIGHT_DISABLED = True
# Source-only prototype: NEVER claim a completed execution without external custody.
PERF_STOP_SIGNALS = frozenset((signal.SIGTERM, signal.SIGINT, signal.SIGALRM))
PERF_LIGHT_BINDING = None
PERF_LIGHT_BINDING_SHA256 = None
PERF_LIGHT_AUTHORITY = None
PERF_LIGHT_WATCHDOG = None
PERF_LIGHT_PHASES = ('perf_compile','perf_fixture')
PERF_MAX_UTC = 1793774133.0

def _canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def _positive_finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0

def _binding_check():
    require(isinstance(PERF_LIGHT_BINDING,dict) and isinstance(PERF_LIGHT_BINDING_SHA256,str) and len(PERF_LIGHT_BINDING_SHA256)==64,'exact binding unbound')
    digest=hashlib.sha256(_canon(PERF_LIGHT_BINDING)).hexdigest()
    require(digest==PERF_LIGHT_BINDING_SHA256,'exact binding hash differs')
    binding=json.loads(_canon(PERF_LIGHT_BINDING))
    require(set(binding)=={'phases','deadline_caps','deadline_mono'},'binding shape')
    phases=binding['phases'];require(isinstance(phases,list) and len(phases)==2 and tuple(x.get('phase') for x in phases)==PERF_LIGHT_PHASES,'two exact phases')
    for x in phases:
        require(set(x)=={'phase','argv','cwd','env'} and isinstance(x['argv'],list) and x['argv'] and
                all(isinstance(a,str) and a and '\0' not in a for a in x['argv']) and
                x['argv'][0].startswith('/') and isinstance(x['cwd'],str) and x['cwd'].startswith('/') and
                isinstance(x['env'],dict) and all(isinstance(k,str) and isinstance(v,str) and '\0' not in k+v for k,v in x['env'].items()),'exact phase input')
    caps=binding['deadline_caps'];require(isinstance(caps,dict) and set(caps)=={'utc','boot','monotonic'} and all(_positive_finite(x) for x in caps.values()),'deadline caps invalid')
    require(caps['utc']<=PERF_MAX_UTC and _positive_finite(binding['deadline_mono']) and binding['deadline_mono']<=caps['monotonic'],'deadline widened')
    return binding,digest

def _check_deadline(binding):
    caps=binding['deadline_caps'];now=(time.time(),time.clock_gettime(time.CLOCK_BOOTTIME),time.monotonic())
    require(all(_positive_finite(x) for x in now) and now[0]<caps['utc'] and now[1]<caps['boot'] and now[2]<caps['monotonic'] and now[2]<binding['deadline_mono'],'deadline elapsed or unknown')
    return binding['deadline_mono']-now[2]

def _gate(callback,binding,digest,label):
    require(callable(callback),label+' unbound')
    before=_canon(binding);provided=json.loads(before)
    value=callback(provided)
    require(value is True,label+' must positively pass')
    require(_canon(provided)==before and _canon(binding)==before and hashlib.sha256(_canon(PERF_LIGHT_BINDING)).hexdigest()==digest,label+' changed binding')
    _check_deadline(binding)

class PerfLightOwner:
    def __init__(self):
        self.state='NEW';self.interrupt=None;self.child=None;self.proof=None;self.results=[];self.error=None;self.handoff={'spawn_attempted':False,'pid':None,'identity':None}
    def _signal(self,signum,frame):
        # Handler only records stop, including the Popen fork/assignment window.
        if self.interrupt is None:self.interrupt=signum
    def _unknown(self,exc):
        self.state='UNKNOWN';self.error=type(exc).__name__+': '+str(exc)
    def _spawn_bound(self,spec,pre,stdout,stderr):
        # Single-task owner and watchdog are external prerequisites. pthread_sigmask
        # only affects this thread; never infer process-wide exclusion from it.
        old=signal.pthread_sigmask(signal.SIG_BLOCK,PERF_STOP_SIGNALS)
        try:
            require(not (set(old)&PERF_STOP_SIGNALS),'stop signal already blocked')
            require(self.interrupt is None and not (set(signal.sigpending())&PERF_STOP_SIGNALS),'stop pending before spawn')
            def child_restore_mask():
                signal.pthread_sigmask(signal.SIG_SETMASK,old)
            self.state='SPAWN_ATTEMPTED';self.handoff={'spawn_attempted':True,'pid':None,'identity':None}
            # preexec_fn exists only for this single-task source prototype. Actual
            # child/runtime safety and external watchdog require separate review.
            self.child=subprocess.Popen(spec['argv'],cwd=spec['cwd'],env=dict(spec['env']),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=child_restore_mask)
            self.handoff['pid']=self.child.pid
            self.proof=ProcessProof(self.child,privileged_wrapper=False,pre_launch=pre)
            require(self.proof.data.get('identity') is not None and self.proof.data['identity'].get('pid')==self.child.pid and not self.proof.data['uncertainties'],'direct identity unavailable')
            self.handoff['identity']=dict(self.proof.data['identity']);self.state='CHILD_BOUND'
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,old)
        require(self.interrupt is None,'stop after child identity')
    def run(self,streams):
        require(PERF_LIGHT_DISABLED is False,'SOURCE_ONLY: perf light owner disabled')
        require(self.state=='NEW','single-use or unknown owner')
        # Claim before every callback: reentrant calls cannot spawn or overwrite custody.
        self.state='CLAIMED';previous={}
        try:
            binding,digest=_binding_check()
            require(isinstance(streams,dict) and set(streams)==set(PERF_LIGHT_PHASES),'exact capture streams required')
            for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):previous[sig]=signal.signal(sig,self._signal)
            _gate(PERF_LIGHT_AUTHORITY,binding,digest,'authority');_gate(PERF_LIGHT_WATCHDOG,binding,digest,'watchdog')
            require(self.interrupt is None,'stop before subreaper')
            enable_subreaper();self.state='READY'
            for spec in binding['phases']:
                require(self.interrupt is None,'stop before phase')
                _gate(PERF_LIGHT_AUTHORITY,binding,digest,'authority');_gate(PERF_LIGHT_WATCHDOG,binding,digest,'watchdog')
                pre=prepare_launch()
                require(hashlib.sha256(_canon(PERF_LIGHT_BINDING)).hexdigest()==digest,'binding drift before spawn')
                _check_deadline(binding)
                # Last check immediately after all pre-spawn gates/observation.
                require(self.interrupt is None,'stop immediately before spawn')
                stdout,stderr=streams[spec['phase']]
                self._spawn_bound(spec,pre,stdout,stderr)
                while True:
                    _gate(PERF_LIGHT_AUTHORITY,binding,digest,'authority');_gate(PERF_LIGHT_WATCHDOG,binding,digest,'watchdog')
                    require(self.interrupt is None,'stop while waiting')
                    self.proof.observe('waiting');require(not self.proof.data['uncertainties'],'census unknown')
                    remaining=_check_deadline(binding)
                    try:code=self.child.wait(timeout=min(0.1,remaining));break
                    except subprocess.TimeoutExpired:continue
                require(type(code) is int,'direct wait missing');_check_deadline(binding)
                raw=self.proof.joined(code)
                require(raw.get('retirement_proven') is True and raw.get('direct_wait',{}).get('exit_code')==code,'descendant closure unproven')
                validate_proof(raw)
                _gate(PERF_LIGHT_WATCHDOG,binding,digest,'watchdog');_gate(PERF_LIGHT_AUTHORITY,binding,digest,'authority')
                require(self.interrupt is None,'stop after join')
                self.results.append({'phase':spec['phase'],'exit_code':code,'proof':raw})
                require(code==0,'phase failed; no next phase')
                self.child=None;self.proof=None;self.state='READY'
            # Deliberately no local success transition: final signal/custody
            # handoff cannot be made atomic by this Python owner alone.
            raise RuntimeError('external custody and finalization unresolved')
        except BaseException as exc:
            self._unknown(exc);raise
        finally:
            for sig,handler in previous.items():signal.signal(sig,handler)
