"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Executable SOURCE proposal. Actual root operations require a fresh exact launch
release and separate late Root/independent authorizations. No actual invocation
is authorized by importing or testing this module.
"""
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import time
import types

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'keeper-phase-adoption-source-1'
FROZEN = {'keeper_protocol.SOURCE-ONLY.py':'942342288186d5ba186297b5a4b65fccff5940f31effe4dce1f2c8607e927027',
          'phase_bootstrap.SOURCE-ONLY.py':'83df82d4e5bdb6310b7510bbcb2b42685ac460e66b93ef69b9c24ef6ba0d3ea7'}
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
LAUNCHER_STATE = Path('/home/holden/mckernel/.git/os-autopilot/state.json')
CUTOFF_PROOF = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW18H-20261026-FIXED-CUTOFF-BINDING.json')
CUTOFF_PROOF_SHA = '2e1d3fa8338e51973cf0af5677e7e256259aff539adb164be0fb53240d834b35'
FIXED_CUTOFFS = [1793100290.0, 882395.5689528405, 897734.6960034363]
WINDOW_ID = 'new18h-20261026-bf8b8eb1832f4c94a0166f20a95642ea'
CUSTODY_ADAPTER = 'exact-root-sudo-reparent1311-outer-typed-absent-v1'
DEADSCAN_INSTALLER = dict(path='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-proc-snapshot-lifecycle-source-1/whole-pair-enoent-correction-source-1/source-origin-correction-source-1/current-reviewer-correction-source-1/deadscan_runtime_bridge.SOURCE-ONLY.py', bytes=10296, sha256='ee69ea61211f43ece62feeb15df885c2d75987effb9c03386491bc33009d8e74')

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def need(ok,reason):
    if not ok: raise ValueError(reason)
def load(path,expected):
    raw=path.read_bytes(); need(sha(raw)==expected,'pipeline-source-pin:'+path.name)
    spec=importlib.util.spec_from_file_location('_pipeline_'+path.stem,path)
    m=importlib.util.module_from_spec(spec)
    exec(compile(raw,str(path),'exec'),m.__dict__)
    return m


old=load(PREVIOUS/'keeper_protocol.SOURCE-ONLY.py',FROZEN['keeper_protocol.SOURCE-ONLY.py'])
phase=load(PREVIOUS/'phase_bootstrap.SOURCE-ONLY.py',FROZEN['phase_bootstrap.SOURCE-ONLY.py'])


def rebound(function, namespace):
    return types.FunctionType(function.__code__, namespace, function.__name__,
                              function.__defaults__, function.__closure__)


def require_launch(packet, raw_sha):
    """Preserve frozen predicates, replacing only explicitly superseded clocks."""
    namespace = dict(old.__dict__, WALL_CUTOFF=FIXED_CUTOFFS[0],
                     MONOTONIC_CUTOFF=FIXED_CUTOFFS[1], BOOT_CUTOFF=FIXED_CUTOFFS[2])
    rebound(old.require_launch, namespace)(packet, raw_sha)
    need(packet.get('window_id') == WINDOW_ID and packet.get('custody_adapter') == CUSTODY_ADAPTER,
         'new-window-and-explicit-custody-adapter-required')


def successor_init(original, instance, *args):
    # A private globals table preserves the frozen source bytes and methods.
    rebound(original, dict(original.__globals__, require_launch=require_launch))(instance, *args)


def absent_outer():
    path = Path('/proc/1060802/stat')
    try:
        path.read_bytes()
    except FileNotFoundError as error:
        need(error.errno == 2 and error.filename == str(path), 'exact-outer-stat-enoent-required')
        return dict(pid=1060802, starttime='80309549', state='ABSENT_EXACT_STAT_ENOENT',
                    historical_join='UNKNOWN', path=str(path))
    raise ValueError('original-outer-no-longer-absent')


def successor_custody(module):
    """Narrow composed successor: same root/sudo bytes, observed reparent only.

    Absence of the historical outer is evidence of absence, never a JOIN. No
    signal, acquisition, descriptor or lock primitive changes here.
    """
    composed = types.ModuleType('_reviewed_absent_outer_custody')
    composed.__dict__.update(module.__dict__)
    def actor_binding(p):
        p.need(os.geteuid() == 0 and os.uname().machine == 'x86_64', 'fixed-root-platform-credentials')
        p.need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == p.BOOT, 'fixed-root-boot')
        grant = p.strict(p.pinned_bytes(p.PREPARATION / 'ROOT-ACTUAL-NORMAL-RETIREMENT-GRANT.json', module.GRANT_SHA))
        argv = grant['argv']; interpreter = argv.index('/home/holden/anaconda3/bin/python3')
        expected = b'\0'.join(word.encode() for word in argv[interpreter:]) + b'\0'
        observed = module.process(p, module.PID, module.START, module.PARENT, module.PGID)
        p.need(observed['command'] == expected, 'fixed-root-exact-granted-command')
        parent = module.process(p, module.PARENT, module.PARENT_START, parent=1311, pgid=module.PGID)
        outer = absent_outer()
        retained = p.strict(p.pinned_bytes(module.IDENTITIES, module.IDENTITIES_SHA, 9945))
        rows = {row['pid']: row for row in retained['processes']}
        for actor in (observed, parent):
            p.need(sha(actor['command']) == rows[actor['pid']]['cmdline_sha256'], 'fixed-root-sudo-exact-argv')
        p.pinned_bytes(p.SOURCE, p.SOURCE_SHA, 128910)
        p.pinned_bytes(p.PREPARATION / 'RELEASE.PASS_EXECUTION_RELEASE.json', p.RELEASE_SHA, 241402)
        need(absent_outer() == outer, 'absent-outer-race')
        return observed, parent, outer
    composed.actor_binding = actor_binding
    composed.acquire_exact_standby = rebound(module.acquire_exact_standby, composed.__dict__)
    return composed


ADOPT_OPERATION = 'ADOPT_AFTER_POSITIVE_RETIREMENT_CURRENT_ABSENCE'


def current_retirement_absence(receipt):
    """Fresh fail-closed process/group observation; never a historical JOIN.

    A disappearing census member is accepted only with a second absent stat and
    absent directory. Permission errors, reused PIDs and unreadable rows stop.
    """
    required = {1060806, 1060803, 1060802}
    children = receipt['physical_observation']['original_capture_control_children']
    need(isinstance(children, list), 'original-capture-children-explicit-list-required')
    for child in children:
        need(isinstance(child, dict) and type(child.get('pid')) is int
             and child['pid'] > 0 and isinstance(child.get('starttime'), str), 'capture-child-identity')
        required.add(child['pid'])
    def absent(pid):
        path=Path('/proc/%d/stat'%pid)
        try: path.read_bytes()
        except FileNotFoundError as error:
            need(error.errno==2 and error.filename==str(path), 'retirement-exact-stat-enoent')
            return
        raise ValueError('retirement-process-still-present:%d'%pid)
    for pid in required: absent(pid)
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal(): continue
        statpath=path/'stat'
        try: raw=statpath.read_bytes()
        except FileNotFoundError as error:
            need(error.errno==2 and error.filename==str(statpath), 'census-exact-stat-enoent')
            # Same whole-pair absence rule as the reviewed diagnostic adapters.
            absent(int(path.name))
            try: path.stat()
            except FileNotFoundError as vanished:
                need(vanished.errno==2 and vanished.filename==str(path), 'retirement-census-exact-directory-enoent')
            else: raise ValueError('retirement-census-partial-disappearance')
            continue
        left, sep, right=raw.rpartition(b') '); fields=right.split()
        need(sep and left.startswith(path.name.encode()+b' (') and len(fields)>=50,
             'retirement-census-malformed-stat')
        need(int(fields[2]) not in (1060802,1060803), 'original-process-group-still-present')
    for pid in required: absent(pid)
    return True


def require_retirement_receipt(p, receipt, packet):
    if packet.get('window_id') != WINDOW_ID:
        # Frozen private fixtures alone retain their historical contract.
        return phase.require_retirement_and_joins(p, receipt, packet)
    need(receipt.get('schema')=='mckernel.current290.retirement-current-absence.v1'
         and receipt.get('operation')==ADOPT_OPERATION
         and receipt.get('target')==p.ROOT_ACTOR and receipt.get('pidfd_exit_ready') is True,
         'positive-owned-root-exit-current-absence-receipt-required')
    need(receipt.get('original_outer')==dict(pid=1060802,starttime='80309549',
             current_state='ABSENT_EXACT_STAT_ENOENT',historical_join='UNKNOWN_UNAVAILABLE'),
         'historical-outer-join-must-remain-unknown')
    need(receipt.get('sudo')==dict(pid=1060803,starttime='80309553',pgid=1060803,
             parent_before_retirement=1311), 'exact-current-sudo-lineage')
    need(receipt.get('protected_state_unchanged') is True
         and receipt.get('only_old_root_actor_signalled') is True
         and receipt.get('historical_join_limitation_explicitly_accepted') is True,
         'retirement-scope-and-explicit-limitation-acceptance-required')
    observation=receipt.get('physical_observation',{})
    need(observation.get('author')=='/root' and observation.get('boot_id')==p.BOOT
         and observation.get('window_id')==WINDOW_ID
         and observation.get('root_and_sudo_absent') is True
         and observation.get('original_groups_zero_members') is True
         and observation.get('no_surviving_original_capture_control_children') is True,
         'root-current-physical-observation-required')
    return current_retirement_absence(receipt)


def install_deadscan(engine, delta, ops):
    """Fail closed until the separate successor installer/review is provided."""
    need(isinstance(delta,dict) and set(delta)=={'installer','root_authorization','source_review'},
         'approved-deadscan-delta-unbound')
    authorization=ops.pinned_document(delta['root_authorization'])
    review=ops.pinned_document(delta['source_review'])
    ref=delta['installer']
    need(ref==DEADSCAN_INSTALLER,'exact-deadscan-successor-installer-required')
    need(authorization.get('author')=='/root' and authorization.get('decision')=='GRANT_EXACT_DEAD_CALLER_LIFECYCLE_DELTA'
         and authorization.get('installer_sha256')==ref['sha256'],'deadscan-installer-new-root-authorization')
    need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY'
         and review.get('reviewer') not in (None,'','/root') and review.get('installer_sha256')==ref['sha256'],
         'independent-deadscan-installer-review-unbound')
    need(authorization.get('source_review')==delta['source_review'],'deadscan-root-authorization-review-reference')
    installer=load(Path(ref['path']),ref['sha256'])
    need(Path(ref['path']).stat().st_size==ref['bytes'],'deadscan-installer-size')
    return installer.install_deadscan_delta(engine,authorization)


def guarded_original_run(engine,p):
    """Exactly one source delta: replace original quarantine refusal with gate."""
    tree=ast.parse(p.pinned_bytes(p.SOURCE,p.SOURCE_SHA,128910))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Transaction')
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    first=node.body[0]
    need(isinstance(first,ast.If) and ast.unparse(first.test)=='os.path.lexists(QUARANTINE)'
         and len(first.body)==1 and isinstance(first.body[0],ast.Raise),'original-quarantine-gate-shape')
    node.name='_adopted_original_run'
    node.body[0]=ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Name(id='self',ctx=ast.Load()),
                                          attr='authorized_quarantine_gate',ctx=ast.Load()),args=[],keywords=[]))
    namespace=dict(engine.__dict__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(Path(__file__).resolve()),'exec'),namespace)
    # Function globals must stay the genuine composed engine namespace, not a
    # frozen copy: original run resolves the approved collector/adapters there.
    return types.FunctionType(namespace[node.name].__code__,engine.__dict__,node.name)


class EmergencyCustody:
    """No post-copy I/O: retains raw integer FDs even if adapter setup failed."""
    def __init__(self,raw,error):
        self.fd,self.pidfd=raw.fd,raw.pidfd
        self.verified,self.error,self.proof=False,str(error),None


class BorrowedTransaction:
    @staticmethod
    def create(m,p,custody,configured,receipt,packet,archive_quarantine,effect_guard):
        require_retirement_receipt(p,receipt,packet)
        need(hasattr(m,'_PROCESS_CENSUS_DELTA_MANIFEST') and hasattr(m,'_DEADSCAN_DELTA_MANIFEST'),
             'both-approved-diagnostic-deltas-required')
        custody.verify_held_after_exit()
        archived=archive_quarantine(m.QUARANTINE,configured['raw_quarantine'])
        need(archived.get('original_preserved') is True,'original-quarantine-additive-archive-required')
        original_validator=m.validate_transaction_inherited_lock
        base=m.Transaction
        guarded=guarded_original_run(m,p)
        duplicate=os.dup(custody.fd)
        def held_validator(fd):
            need(fd==duplicate,'borrowed-exact-private-description')
            custody.verify_held_after_exit()
            before,named=os.fstat(fd),os.fstat(custody.fd)
            need(all(getattr(before,key)==getattr(named,key) for key in old.FIELDS),'borrowed-copy-metadata')
            need(not os.get_inheritable(fd) and fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDONLY,
                 'borrowed-private-readonly-copy')
            expected=custody.proof['custody']['lock']
            need(custody.proof.get('old_actor')==packet['old_actor'],'borrowed-authenticated-old-actor-lineage')
            need(p.description_lock_rows(os.getpid(),fd)==[expected],'borrowed-old-root-ofd-lineage')
            return True
        class Borrowed(base):
            def __init__(self): raise ValueError('explicit-borrowed-construction-only')
            def prepare(self): raise ValueError('original-plan-must-never-be-reprepared')
            def pinned(self):
                effect_guard()
                if packet.get('window_id')==WINDOW_ID:
                    require_retirement_receipt(p,receipt,packet)
                    custody.verify_held_after_exit()
                return base.pinned(self)
            def close(self):
                # Own os.dup only. Never LOCK_UN, never close custody.fd, never
                # call oldrecover or its finally. Keep original validator context
                # until the final own descriptor has been closed.
                for name in ('mfd','nfd','fd','rfd'):
                    fd=getattr(self,name,None)
                    if fd is not None:
                        os.close(fd); setattr(self,name,None)
                self.root_locked=False
                if m.validate_transaction_inherited_lock is held_validator:
                    m.validate_transaction_inherited_lock=original_validator
                custody.verify_held_after_exit()
            def authorized_quarantine_gate(self):
                need(self.mutation_authorized and not self.run_entered,'new-shared-only-root-authorization-required')
                self.run_entered=True
                self.pinned(); m.protected_files()
                need(m.read_bounded(m.PLAN)==configured['raw_plan'] and m.read_bounded(m.JOURNAL)==configured['raw_journal'],
                     'exact-original-plan-four-event-prefix-required')
                rows,states=self.state(self.original_plan)
                need(len(rows)==4 and states==['after_release','before_exchange'],'only-shared-initial-phase')
                self.check_original_quarantine_and_common()
            def check_original_quarantine_and_common(self):
                need(m.read_bounded(m.QUARANTINE)==configured['raw_quarantine'],'original-quarantine-changed')
                need(m.observe_identity(m.QUARANTINE)==self.original_quarantine_metadata,'original-quarantine-inode-metadata-changed')
                need(not os.path.lexists(m.ATTEMPT),'completed-common-active-reappeared')
                record=configured['original_release']['observation']['retained_exclusions'][0]
                path=Path(self.original_plan['records'][0][1])/self.original_plan['records'][0][2]
                need(m.observe_identity(path)==dict(record,path=str(path)),'completed-common-archive-changed')
            def run_shared(self):
                need(self.mutation_authorized and not self.run_entered,'shared-mutator-one-call-only')
                try:
                    result=guarded(self,True)
                    self.check_original_quarantine_and_common()
                    rows,states=self.state(self.original_plan)
                    need(len(rows)==9 and states==['after_release','after_release'],'shared-terminal-nine-events-required')
                    return result
                finally:
                    # Caller/keeper retains its own genuine description on error.
                    self.close()
            def run(self,execute): raise ValueError('use-separately-authorized-run_shared-only')
        tx=object.__new__(Borrowed)
        tx.rfd,tx.fd,tx.nfd,tx.mfd=duplicate,None,None,None
        tx.root_locked,tx.root_lock_inherited,tx.mutation_started=True,True,True
        tx.mutation_authorized,tx.run_entered=False,False
        try:
            tx.original_quarantine_metadata=m.observe_identity(m.QUARANTINE)
            m.validate_transaction_inherited_lock=held_validator
            tx.fd,tx.chain=m.directory(m.ROOT)
            tx.nfd,tx.namespace_chain=m.directory(m.NAMESPACE)
            tx.pinned(); tx.lock(False); m.protected_files()
            tx.original_plan=tx.load_plan()
            need(m.canonical(tx.original_plan)+b'\n'==configured['raw_plan'],'borrowed-original-plan-provenance')
            p.require_partial_phase(tx,tx.original_plan,configured['raw_plan'],configured['raw_journal'])
            tx.context_manifest=dict(schema='mckernel.current290.borrowed-held-root-context.v1',
                 inherited=True,old_root_ofd_pid=1060806,keeper_fd=custody.fd,borrowed_fd=duplicate,
                 old_release_canonical_sha256=p.RELEASE_CANONICAL_SHA,old_plan_canonical_sha256=p.PLAN_CANONICAL_SHA,
                 validator_source_sha256=sha(Path(__file__).read_bytes()),original_quarantine_preserved=True,
                 own_close_semantics='close-own-dup-and-auxiliary-fds-only-no-LOCK_UN',quarantine_archive=archived)
            return tx
        except BaseException:
            tx.close()
            raise



class SafeLocalCustody(old.LocalCustody):
    def close_new_copy_while_old_alive(self):
        self.verify_old_alive()
        os.close(self.pidfd)
        os.close(self.fd)
        self.closed=True


class PipelineOps(old.LocalOps):
    def __init__(self,packet,raw,evidence):
        successor_init(old.LocalOps.__init__, self, packet, raw, evidence)
        self.require_custody_adapter_review()
        self.custody_module=successor_custody(self.custody_module)
        self.raw_hold=None
        self.capture_sequence=0
        self.mutation_consumed=False
        self.require_pipeline_sources(packet)

    def clock_check(self):
        proof_raw=CUTOFF_PROOF.read_bytes()
        need(sha(proof_raw)==CUTOFF_PROOF_SHA,'exact-parent-fixed-cutoff-binding')
        proof=json.loads(proof_raw)
        need(proof.get('window_id')==WINDOW_ID and proof.get('fixed_cutoffs')==FIXED_CUTOFFS
             and proof.get('credit_run_id')=='7f4af94a83b14cc08f97401f5891d965', 'same-new18h-parent-cutoffs')
        need(time.time()<FIXED_CUTOFFS[0] and time.monotonic()<FIXED_CUTOFFS[1]
             and time.clock_gettime(time.CLOCK_BOOTTIME)<FIXED_CUTOFFS[2], 'keeper-fixed-parent-window-ended')
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==proof['boot_id'], 'same-parent-boot')
        state=json.loads(LAUNCHER_STATE.read_bytes())
        need(state.get('thread_id')==proof['thread_id'] and state.get('phase')=='running'
             and state.get('stop_reason') is None and state.get('credit_budget_error') is None,
             'launcher-stopped-or-credit-service-guard-hold')

    def require_custody_adapter_review(self):
        review=self.pinned_document(self.packet.get('custody_adapter_review'))
        need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY'
             and review.get('reviewer') not in (None,'','/root')
             and review.get('custody_adapter')==CUSTODY_ADAPTER
             and review.get('runtime_sha256')==sha(Path(__file__).read_bytes()),
             'independent-exact-absent-outer-adapter-review-required')

    def require_pipeline_sources(self,packet):
        refs=packet.get('pipeline_sources')
        need(isinstance(refs,dict) and set(refs)=={'runtime','entry','outer'},'complete-executable-pipeline-source-refs')
        for name,ref in refs.items():
            path=Path(ref['path']); need(path.parent==HERE,'fixed-pipeline-source-parent')
            self.p.pinned_bytes(path,ref['sha256'],ref['bytes'])
        need(refs['runtime']['sha256']==sha(Path(__file__).read_bytes()),'exact-runtime-source')

    def acquire(self):
        # Persist the raw copy BEFORE any fallible adapter read/fstat/import.
        raw=self.custody_module.acquire_exact_standby()
        self.raw_hold=raw
        try: return SafeLocalCustody(self.custody_module,raw)
        except BaseException as error: return EmergencyCustody(raw,type(error).__name__+': '+str(error))

    def publish_bytes(self,name,raw):
        # Full bounded diagnostic captures, not truncated failure prefixes.
        need(self.evidence_fd is not None and Path(name).name==name and len(raw)<=32<<20,'full-capture-file-bound')
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.evidence_fd)
        try:
            os.fchown(fd,1000,1000)
            remaining=memoryview(raw)
            while remaining:
                n=os.write(fd,remaining); need(n>0,'capture-write-no-progress'); remaining=remaining[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(self.evidence_fd)
        return dict(path=str(self.evidence/name),bytes=len(raw),sha256=sha(raw))

    def require_operation(self,envelope,operation):
        need(isinstance(envelope,dict) and envelope.get('operation')==operation,'late-operation-envelope')
        grant=self.pinned_document(envelope['root_grant'])
        review=self.pinned_document(envelope['independent_execution_review'])
        need(grant.get('operation')==operation and grant.get('author')=='/root'
             and grant.get('keeper')==self.self_identity and grant.get('launch_sha256')==sha(self.raw_packet)
             and grant.get('target')==self.packet['old_actor']
             and grant.get('pipeline_sources')==self.packet['pipeline_sources']
             and grant.get('source_hashes')==self.packet['source_hashes'],'late-root-operation-exact-binding')
        need(review.get('status')=='PASS_EXECUTION_RELEASE' and review.get('reviewer') not in (None,'','/root')
             and review.get('root_grant_sha256')==envelope['root_grant']['sha256']
             and review.get('pipeline_sources')==self.packet['pipeline_sources'],'late-independent-operation-release')
        return grant

    def authorize_retirement(self,command,packet,raw_sha):
        self.require_operation(command,'RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY')
        super().authorize_retirement(command,packet,raw_sha)

    def configure_phase(self):
        configured=super().configure_phase()
        delta=self.packet.get('deadscan_delta')
        need(isinstance(delta,dict),'approved-deadscan-delta-null-no-retirement')
        manifest=install_deadscan(self.engine,delta,self)
        self.publish('DEADSCAN-DIAGNOSTIC-COMPOSITION.json',manifest)
        self.install_raw_capture()
        return configured

    def install_raw_capture(self):
        m=self.engine; original=m.subprocess; owner=self
        class CaptureProxy:
            def __getattr__(self,name): return getattr(original,name)
            def run(self,*args,**kwargs):
                seq=owner.capture_sequence; owner.capture_sequence+=1
                try:
                    result=original.run(*args,**kwargs)
                except subprocess.TimeoutExpired as error:
                    stdout=owner.publish_bytes('ROOT-COMMAND-%04d.stdout'%seq,error.stdout or b'')
                    stderr=owner.publish_bytes('ROOT-COMMAND-%04d.stderr'%seq,error.stderr or b'')
                    owner.publish('ROOT-COMMAND-%04d.RESULT.json'%seq,dict(argv=args[0],error='TimeoutExpired',stdout=stdout,stderr=stderr))
                    raise
                stdout=owner.publish_bytes('ROOT-COMMAND-%04d.stdout'%seq,result.stdout)
                stderr=owner.publish_bytes('ROOT-COMMAND-%04d.stderr'%seq,result.stderr)
                owner.publish('ROOT-COMMAND-%04d.RESULT.json'%seq,dict(argv=args[0],returncode=result.returncode,stdout=stdout,stderr=stderr))
                return result
        m.subprocess=CaptureProxy()
        self.publish('RAW-CAPTURE-COMPOSITION.json',dict(changed_dependency='subprocess',
             delegated_module='stdlib subprocess',intercepted_method='run',source_sha256=sha(Path(__file__).read_bytes()),
             stdout_stderr='complete bytes;32MiB per-file ceiling;failure retains custody'))

    def authorize_join_receipt(self,receipt,packet,raw_sha):
        need(isinstance(receipt,dict) and set(receipt)=={'receipt','root_grant','independent_execution_review'},
             'typed-current-absence-authorization-envelope')
        auth=dict(operation=ADOPT_OPERATION,root_grant=receipt['root_grant'],
                  independent_execution_review=receipt['independent_execution_review'])
        grant=self.require_operation(auth,ADOPT_OPERATION)
        need(grant.get('receipt_sha256')==receipt['receipt']['sha256']
             and grant.get('historical_join_limitation_explicitly_accepted') is True
             and grant.get('custody_adapter')==CUSTODY_ADAPTER,
             'exact-root-current-absence-replacement-authority')
        actual=self.pinned_document(receipt['receipt'])
        need(actual.get('keeper')==self.self_identity and actual.get('launch_sha256')==raw_sha
             and actual.get('window_id')==WINDOW_ID, 'current-absence-receipt-launch-binding')
        refs=actual.get('retained_capture_refs')
        need(isinstance(refs,list) and refs, 'preserved-original-captures-required')
        for ref in refs:
            self.p.pinned_bytes(Path(ref['path']),ref['sha256'],ref['bytes'])
        require_retirement_receipt(self.p,actual,packet)
        self.retirement_receipt=actual
        return actual

    def bootstrap(self,configured,custody,receipt,packet):
        tx=BorrowedTransaction.create(self.engine,self.p,custody,configured,receipt,packet,self.archive_original_quarantine,self.clock_check)
        self.publish('BORROWED-CUSTODY-CONTEXT.json',tx.context_manifest)
        return tx

    def dump_diagnostics(self,label):
        if self.engine is not None:
            self.publish(label+'.DEAD-CALLER-OBSERVATIONS.json',getattr(self.engine,'DEAD_CALLER_OBSERVATIONS',[]))
        usage=resource.getrusage(resource.RUSAGE_SELF)
        self.publish(label+'.JOB-METRICS.json',dict(pid=os.getpid(),user_seconds=usage.ru_utime,
                     system_seconds=usage.ru_stime,peak_rss_kib=usage.ru_maxrss,monotonic=time.monotonic(),
                     wall=time.time(),child_usage=dict(user_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,
                          system_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime)))


class PipelineKeeper(old.Keeper):
    def __init__(self, packet, raw_sha, ops):
        successor_init(old.Keeper.__init__, self, packet, raw_sha, ops)

    def finish_shared(self,command):
        need(self.state=='PHASE_BOOTSTRAP_READY_CUSTODY_HELD' and not self.ops.mutation_consumed,'shared-stage-once-after-positive-original-joins')
        self.ops.clock_check()
        grant=self.ops.require_operation(command,'FINISH_REMAINING_SHARED_ONLY')
        need(grant.get('borrowed_context_sha256')==sha(canonical(self.tx.context_manifest))
             and grant.get('old_plan_sha256')==self.ops.p.PLAN_CANONICAL_SHA
             and grant.get('old_journal_sha256')==self.ops.p.JOURNAL_SHA,'shared-new-root-authority-provenance')
        self.custody.verify_held_after_exit()
        require_retirement_receipt(self.ops.p,self.ops.retirement_receipt,self.packet)
        self.ops.mutation_consumed=True
        self.ops.publish('SHARED-MUTATION-BUDGET-CONSUMED.json',dict(root_grant=command['root_grant'],remaining_indices=[1],original_quarantine_retained=True))
        try:
            self.ops.clock_check()
            self.tx.mutation_authorized=True
            result=self.tx.run_shared()
            self.custody.verify_held_after_exit()
            self.ops.publish('SHARED-ONLY-RESULT.json',result)
            self.ops.dump_diagnostics('SHARED-COMPLETE')
            self.state='SHARED_DONE_CUSTODY_HELD'
        except BaseException as error:
            self.state='HELD_QUARANTINE'
            self.ops.publish('SHARED-FAILURE-HOLD.json',dict(error=type(error).__name__+': '+str(error),custody_retained=True,retry=False))
            self.ops.dump_diagnostics('SHARED-FAILURE')
        return self.state

    def release_after_shared(self,command):
        need(self.state=='SHARED_DONE_CUSTODY_HELD','terminal-shared-proof-before-release')
        grant=self.ops.require_operation(command,'RELEASE_KEEPER_AFTER_SHARED_TERMINAL')
        m=self.ops.engine
        self.ops.clock_check()
        self.custody.verify_held_after_exit()
        require_retirement_receipt(self.ops.p,self.ops.retirement_receipt,self.packet)
        need(all(getattr(self.tx,name,None) is None for name in ('rfd','mfd','fd','nfd')),'borrowed-descriptors-must-be-closed')
        m.protected_files()
        need(not m.census() and not os.path.lexists(m.ATTEMPT) and not os.path.lexists(m.SHARED),'terminal-container-and-records-absent')
        receipt=self.ops.pinned_document(command['terminal_receipt'])
        need(grant.get('terminal_receipt_sha256')==command['terminal_receipt']['sha256']
             and receipt.get('keeper')==self.ops.self_identity and receipt.get('shared_result_accepted') is True
             and receipt.get('current_retirement_absence_accepted') is True
             and receipt.get('historical_join_limitation_explicitly_accepted') is True
             and receipt.get('root_custody_held') is True,
             'fresh-root-terminal-receipt-required')
        self.ops.dump_diagnostics('PRE-FINAL-RELEASE')
        self.ops.publish('FINAL-CLOSE-BUDGET-CONSUMED.json',dict(root_grant=command['root_grant'],external_current_postjoin_physical_proof_still_required=True))
        self.custody.verify_held_after_exit()
        require_retirement_receipt(self.ops.p,self.ops.retirement_receipt,self.packet)
        self.ops.clock_check()
        # Explicitly authorized FINAL close, no LOCK_UN and no reacquisition.
        os.close(self.custody.pidfd)
        os.close(self.custody.fd); self.custody.closed=True
        self.ops.raw_hold=None
        self.state='ROOT_CUSTODY_CLOSED_EXTERNAL_POSTJOIN_REQUIRED'
        return self.state

    def serve(self,next_command):
        try:
            self.start()
            while True:
                if self.state=='VERIFIED_STANDBY' and self.ops.now()>=self.deadline: self.expire_before_retirement()
                if self.state in ('CLOSED_NEW_COPY_OLD_ACTOR_RETAINED','ROOT_CUSTODY_CLOSED_EXTERNAL_POSTJOIN_REQUIRED'): return self.state
                command=next_command()
                if command is not None:
                    operation=command.get('operation')
                    if operation=='RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY': self.retire(command)
                    elif operation==ADOPT_OPERATION: self.adopt_after_joins(command['receipt'])
                    elif operation=='FINISH_REMAINING_SHARED_ONLY': self.finish_shared(command)
                    elif operation=='RELEASE_KEEPER_AFTER_SHARED_TERMINAL': self.release_after_shared(command)
                    else: raise ValueError('unrecognized-late-root-operation')
                self.ops.sleep(.2)
        except BaseException as error:
            if self.custody is None and self.ops.raw_hold is None: raise
            self.state='HELD_QUARANTINE'
            try:
                self.ops.publish('PIPELINE-EXCEPTION-HOLD.json',dict(error=type(error).__name__+': '+str(error),custody_retained=True,retry=False))
                self.ops.dump_diagnostics('PIPELINE-FAILURE')
            finally: self.ops.quarantine_wait()


def run_pipeline(packet,raw_packet,evidence,next_command):
    """Called only by the separately released exact executable entry wrapper."""
    need(os.getuid()==os.geteuid()==0,'root-pipeline-requires-exact-root-execution-release')
    need(sha(raw_packet)==sha(canonical(packet)+b'\n') or json.loads(raw_packet)==packet,'exact-launch-packet-bytes')
    ops=PipelineOps(packet,raw_packet,evidence)
    # External entry wrapper binds launch Rootgrant/review before this function.
    try:
        return PipelineKeeper(packet,sha(raw_packet),ops).serve(next_command)
    except BaseException:
        if ops.raw_hold is not None: ops.quarantine_wait()
        raise
