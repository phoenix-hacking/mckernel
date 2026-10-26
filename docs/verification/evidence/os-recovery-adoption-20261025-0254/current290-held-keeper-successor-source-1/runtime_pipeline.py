"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed successor over immutable0a67: live held keeper is the transfer/retire target;
original root remains immutable flock/plan origin. Definitions only on import.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import sys
import types

HERE=Path(__file__).resolve().parent
E=HERE.parent
FROZEN=E/'current290-partial-quarantine-reconciliation-source-1/keeper-capture-shared-mutator-source-1/runtime_pipeline.py'
FROZEN_SHA='0a67af9b28ac480960dbcaa2553b9b262cf90f1f96618beb818392018715648c'
RETIRE='RETIRE_EXACT_PREDECESSOR_KEEPER_PIDFD_ONLY'
ADOPT='ADOPT_AFTER_POSITIVE_PREDECESSOR_JOINS'


def need(ok,why):
    if not ok:raise ValueError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(path,expected):
    raw=path.read_bytes();need(sha(raw)==expected,'successor-runtime-source-pin:'+path.name)
    module=types.ModuleType('_successor_'+path.stem);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

base=load(FROZEN,FROZEN_SHA)
# Exact local helper bindings are included in the reviewed runtime source itself.
ADAPTER_SHA='a69bde796240645d1527b8621fd8992e09fdb9982f7165e13bf5b17fc4800474'
BRIDGE_SHA='5d5af47e2640f0d9612db336af800cccd49ff6f31342f21f1e2cfa0ba05af3c1'
LIFECYCLE=dict(path=str(E/'current290-partial-quarantine-reconciliation-source-1/keeper-capture-shared-mutator-source-1/lifecycle-exhaustion-repair-source-1/lifecycle_runtime_bridge.SOURCE-ONLY.py'),bytes=11597,sha256='021165e4fb4d67bb89574c9c0643340731572dec7702ed77892e16daa014a759')
successor=load(HERE/'keeper_custody_successor.py',ADAPTER_SHA)
# The bridge uses this exact authenticated module; no search-path import occurs.
bridge_raw=(HERE/'custody_runtime_bridge.py').read_bytes()
need(sha(bridge_raw)==BRIDGE_SHA,'successor-runtime-bridge-pin')
bridge=types.ModuleType('_successor_bridge');bridge.__file__=str(HERE/'custody_runtime_bridge.py')
import ast
bridge_tree=ast.parse(bridge_raw)
imports=[node for node in bridge_tree.body if isinstance(node,ast.Import) and any(a.name=='keeper_custody_successor' for a in node.names)]
need(len(imports)==1 and len(imports[0].names)==1 and imports[0].names[0].asname=='successor','exact-bridge-local-import-shape')
bridge_tree.body.remove(imports[0]);bridge.successor=successor
exec(compile(bridge_tree,bridge.__file__,'exec'),bridge.__dict__)
PREDECESSOR=dict(pid=1193473,starttime='83392603',parent=1193470,pgid=1193468,fd=6,boot_id=successor.BOOT)
SUDO=dict(pid=1193470,starttime='83392595',parent=1193469,pgid=1193468)
OUTER=dict(pid=1193469,starttime='83392586',parent=1193468,pgid=1193468)


def exact_absence(pid):
    path=Path('/proc/%d/stat'%pid)
    try:path.read_bytes()
    except FileNotFoundError as error:
        need(error.errno==2 and error.filename==str(path),'successor-exact-current-stat-absence')
        return
    raise ValueError('predecessor-actor-still-present:%d'%pid)

def current_predecessor_absence():
    """Fresh current state only; no JOIN is inferred from absence."""
    required=(1193473,1193470,1193469,1193468)
    for pid in required:exact_absence(pid)
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        statpath=path/'stat'
        try:raw=statpath.read_bytes()
        except FileNotFoundError as error:
            need(error.errno==2 and error.filename==str(statpath),'successor-census-exact-stat-enoent')
            exact_absence(int(path.name))
            try:path.stat()
            except FileNotFoundError as gone:
                need(gone.errno==2 and gone.filename==str(path),'successor-census-exact-directory-enoent')
            else:raise ValueError('successor-census-partial-disappearance')
            continue
        left,sep,right=raw.rpartition(b') ');fields=right.split()
        need(sep and left.startswith(path.name.encode()+b' (') and len(fields)>=50,'successor-census-malformed-stat')
        need(int(fields[2])!=1193468,'predecessor-process-group-still-present')
    for pid in required:exact_absence(pid)
    return True


def require_predecessor_receipt(ops,receipt):
    need(receipt.get('schema')=='mckernel.current290.predecessor-keeper-positive-joins.v1'
      and receipt.get('author')=='/root' and receipt.get('operation')==ADOPT
      and receipt.get('predecessor_custodian')==PREDECESSOR
      and receipt.get('keeper')==ops.self_identity and receipt.get('launch_sha256')==sha(ops.raw_packet)
      and receipt.get('window_id')==base.WINDOW_ID
      and receipt.get('pidfd_exit_ready') is True
      and receipt.get('only_predecessor_keeper_signalled') is True
      and receipt.get('original_root_retirement_replayed') is False
      and receipt.get('protected_state_unchanged') is True,'positive-predecessor-joins-exact-receipt')
    join_ref=receipt['sudo_direct_join']
    need(isinstance(join_ref,dict) and join_ref.get('path')==str(successor.CAPTURE/'OUTER/DIRECT-CHILD-JOIN.json'),
         'exact-predecessor-outer-sudo-join-capture-path')
    sudo=ops.pinned_document(join_ref)
    need(sudo.get('pid')==SUDO['pid'] and sudo.get('starttime')==SUDO['starttime']
      and sudo.get('direct_join') is True and type(sudo.get('wait_status')) is int
      and type(sudo.get('exit_code')) is int,'actual-sudo-direct-wait-capture-required')
    outer=ops.pinned_document(receipt['outer_tool_join'])
    need(outer.get('author')=='/root' and outer.get('tool_session_id')==1416
      and outer.get('outer')==OUTER and outer.get('status')=='ACTUAL_TOOL_COMPLETED'
      and outer.get('actual_tool_result_retained') is True
      and outer.get('join_inferred_from_absence') is False,'actual-tool1416-result-required')
    refs=outer.get('actual_tool_result_refs')
    need(isinstance(refs,list) and refs,'actual-tool-result-bytes-required')
    for ref in refs:ops.p.pinned_bytes(Path(ref['path']),ref['sha256'],ref['bytes'])
    need(receipt.get('predecessor_group_zero_members') is True
      and receipt.get('predecessor_wrapper_absent') is True,'positive-current-predecessor-completion-required')
    return current_predecessor_absence()


class SuccessorOps(base.PipelineOps):
    def __init__(self,packet,raw,evidence):
        self.predecessor_receipt=None
        super().__init__(packet,raw,evidence)
        need(packet.get('predecessor_custodian')==PREDECESSOR and packet.get('predecessor_tool_session_id')==1416,
             'exact-predecessor-source-launch-target')
        bridge.install_custody_successor(self,packet.get('custody_successor_composition'))

    def require_custody_adapter_review(self):
        review=self.pinned_document(self.packet.get('custody_adapter_review'))
        need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY'
          and review.get('reviewer') not in (None,'','/root')
          and review.get('custody_adapter')==successor.ADAPTER
          and review.get('runtime_sha256')==sha(Path(__file__).read_bytes())
          and review.get('frozen_runtime_sha256')==FROZEN_SHA
          and review.get('adapter_sha256')==ADAPTER_SHA and review.get('bridge_sha256')==BRIDGE_SHA,
          'independent-exact-successor-runtime-source-review')

    def require_pipeline_sources(self,packet):
        refs=packet.get('pipeline_sources')
        need(isinstance(refs,dict) and set(refs)=={'runtime','entry','outer'},'complete-successor-pipeline-refs')
        for role,filename in [('runtime','runtime_pipeline.py'),('entry','capture_entry.py'),('outer','capture_outer.py')]:
            ref=refs[role];need(Path(ref['path'])==HERE/filename,'closed-successor-pipeline-source-path')
            self.p.pinned_bytes(Path(ref['path']),ref['sha256'],ref['bytes'])
        need(refs['runtime']['sha256']==sha(Path(__file__).read_bytes()),'exact-successor-runtime-source')

    def clock_check(self):
        super().clock_check()
        if self.predecessor_receipt is not None:
            require_predecessor_receipt(self,self.predecessor_receipt)

    def require_operation(self,envelope,operation):
        need(isinstance(envelope,dict) and envelope.get('operation')==operation,'successor-late-operation-envelope')
        grant=self.pinned_document(envelope['root_grant']);review=self.pinned_document(envelope['independent_execution_review'])
        target=PREDECESSOR if operation==RETIRE else self.packet['old_actor']
        bindings=dict(operation=operation,author='/root',keeper=self.self_identity,
           launch_sha256=sha(self.raw_packet),target=target,pipeline_sources=self.packet['pipeline_sources'],
           source_hashes=self.packet['source_hashes'],predecessor_custodian=PREDECESSOR,
           successor_custody_adapter=successor.ADAPTER,lock_origin_pid=1060806)
        need(all(grant.get(k)==v for k,v in bindings.items()),'late-successor-root-operation-exact-binding')
        need(review.get('status')=='PASS_EXECUTION_RELEASE' and review.get('reviewer') not in (None,'','/root')
           and review.get('root_grant_sha256')==envelope['root_grant']['sha256']
           and review.get('pipeline_sources')==self.packet['pipeline_sources'],'late-successor-independent-operation-release')
        return grant

    def authorize_retirement(self,command,packet,raw_sha):
        grant=self.require_operation(command,RETIRE)
        need(grant.get('pidfd_sigkill_budget')==1 and grant.get('numeric_or_group_signal_budget')==0
           and grant.get('predecessor_launch_sha256')==successor.PINS['launch'][2],
           'one-new-predecessor-pidfd-retirement-only')

    def positive_pidfd_exit(self,pidfd):
        poll=select.poll();poll.register(pidfd,select.POLLIN)
        need(any(fd==pidfd and mask&select.POLLIN for fd,mask in poll.poll(5000)),
             'positive-predecessor-pidfd-exit-deadline')
        return dict(target=PREDECESSOR,pidfd_exit_ready=True,actual_sudo_and_tool1416_joins_pending=True,
                    original_root_retirement_replayed=False)

    def configure_phase(self):
        configured=super().configure_phase()
        delta=self.packet.get('confirmed_exit_delta')
        need(isinstance(delta,dict) and set(delta)=={'installer','root_authorization','source_review'},'approved-confirmed-exit-delta-required')
        need(delta['installer']==LIFECYCLE,'closed-confirmed-exit-installer')
        auth=self.pinned_document(delta['root_authorization']);review=self.pinned_document(delta['source_review'])
        need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY' and review.get('reviewer') not in (None,'','/root')
           and review.get('installer_sha256')==LIFECYCLE['sha256']
           and auth.get('source_review')==delta['source_review'],'confirmed-exit-independent-source-review')
        installer=load(Path(LIFECYCLE['path']),LIFECYCLE['sha256'])
        need(Path(LIFECYCLE['path']).stat().st_size==LIFECYCLE['bytes'],'confirmed-exit-installer-size')
        manifest=installer.install_confirmed_exit_delta(self.engine,auth)
        self.publish('CONFIRMED-EXIT-SOURCE-COMPOSITION.json',manifest)
        return configured

    def authorize_join_receipt(self,envelope,packet,raw_sha):
        need(isinstance(envelope,dict) and set(envelope)=={'receipt','root_grant','independent_execution_review'},'successor-join-authorization-envelope')
        command=dict(operation=ADOPT,root_grant=envelope['root_grant'],independent_execution_review=envelope['independent_execution_review'])
        grant=self.require_operation(command,ADOPT);actual=self.pinned_document(envelope['receipt'])
        need(grant.get('receipt_sha256')==envelope['receipt']['sha256'],'successor-join-receipt-root-binding')
        require_predecessor_receipt(self,actual)
        original=self.pinned_document(actual['original_root_retirement_receipt'])
        base.require_retirement_receipt(self.p,original,packet)
        need(original.get('keeper')==dict(pid=1193473,starttime='83392603',pgid=1193468)
           and original.get('launch_sha256')==successor.PINS['launch'][2], 'retained-original-root-receipt-source-binding')
        self.predecessor_receipt,self.retirement_receipt=actual,original
        return original

    def bootstrap(self,configured,custody,receipt,packet):
        need(self.predecessor_receipt is not None and hasattr(self.engine,'_CONFIRMED_EXIT_DELTA_MANIFEST'),
             'positive-predecessor-joins-and-confirmed-exit-delta-before-bootstrap')
        require_predecessor_receipt(self,self.predecessor_receipt)
        return super().bootstrap(configured,custody,receipt,packet)


class SuccessorKeeper(base.PipelineKeeper):
    def retire(self,command):
        need(self.state=='VERIFIED_STANDBY' and not self.command_consumed,'successor-retirement-once-from-standby')
        self.ops.clock_check();need(self.ops.now()<self.deadline,'successor-retirement-before-standby-deadline')
        self.ops.authorize_retirement(command,self.packet,self.raw_sha)
        self.custody.verify_old_alive();self.configured=self.ops.configure_phase();self.custody.verify_old_alive()
        self.ops.clock_check();need(self.ops.now()<self.deadline,'successor-after-configure-deadline')
        self.command_consumed=self.retirement_intent_consumed=True
        self.state='PREDECESSOR_RETIREMENT_ATTEMPTED_CUSTODY_HELD'
        try:
            self.ops.publish('PREDECESSOR-RETIREMENT-BUDGET-CONSUMED.json',dict(launch_sha256=self.raw_sha,
                command_sha256=sha(canonical(command)),target=PREDECESSOR,pidfd_sigkill_calls_allowed=1,
                numeric_or_group_signal_calls=0,original_root_retirement_replayed=False))
            self.custody.verify_old_alive();self.ops.clock_check()
            need(self.ops.now()<self.deadline,'successor-immediate-retirement-deadline')
            self.signal_call_attempted=True;self.ops.sole_pidfd_sigkill(self.custody.pidfd)
            exit_proof=self.ops.positive_pidfd_exit(self.custody.pidfd);self.custody.verify_held_after_exit()
            self.ops.publish('PREDECESSOR-POSITIVE-PIDFD-EXIT.json',exit_proof)
            self.state='PREDECESSOR_EXITED_AWAITING_ACTUAL_JOINS'
        except BaseException as error:
            self.state='HELD_QUARANTINE';self.ops.publish('PREDECESSOR-RETIREMENT-UNCERTAINTY-HOLD.json',
               dict(error=type(error).__name__+': '+str(error),custody_retained=True,retry=False,signal_call_attempted=self.signal_call_attempted))
        return self.state

    def adopt_after_joins(self,envelope):
        need(self.state=='PREDECESSOR_EXITED_AWAITING_ACTUAL_JOINS','positive-predecessor-exit-first')
        try:
            receipt=self.ops.authorize_join_receipt(envelope,self.packet,self.raw_sha)
            self.custody.verify_held_after_exit()
            self.tx=self.ops.bootstrap(self.configured,self.custody,receipt,self.packet)
            self.custody.verify_held_after_exit()
            self.ops.publish('PHASE-BOOTSTRAP-READY-CUSTODY-HELD.json',dict(old_plan_unmodified=True,
               old_journal_prefix_events=4,remaining_indices=[1],predecessor_joins_verified=True,cleanup_executed=False))
            self.state='PHASE_BOOTSTRAP_READY_CUSTODY_HELD'
        except BaseException as error:
            self.state='HELD_QUARANTINE';self.ops.publish('SUCCESSOR-ADOPTION-HOLD.json',dict(error=str(error),custody_retained=True,retry=False))
        return self.state

    def serve(self,next_command):
        try:
            self.start()
            while True:
                if self.state=='VERIFIED_STANDBY' and self.ops.now()>=self.deadline:self.expire_before_retirement()
                if self.state in ('CLOSED_NEW_COPY_OLD_ACTOR_RETAINED','ROOT_CUSTODY_CLOSED_EXTERNAL_POSTJOIN_REQUIRED'):return self.state
                command=next_command()
                if command is not None:
                    operation=command.get('operation')
                    if operation==RETIRE:self.retire(command)
                    elif operation==ADOPT:self.adopt_after_joins(command['receipt'])
                    elif operation=='FINISH_REMAINING_SHARED_ONLY':self.finish_shared(command)
                    elif operation=='RELEASE_KEEPER_AFTER_SHARED_TERMINAL':self.release_after_shared(command)
                    else:raise ValueError('unknown-successor-operation')
                self.ops.sleep(.2)
        except BaseException as error:
            if self.custody is None and self.ops.raw_hold is None:raise
            self.state='HELD_QUARANTINE'
            try:self.ops.publish('SUCCESSOR-PIPELINE-EXCEPTION-HOLD.json',dict(error=str(error),custody_retained=True,retry=False))
            finally:self.ops.quarantine_wait()


def run_pipeline(packet,raw_packet,evidence,next_command):
    need(os.getuid()==os.geteuid()==0,'successor-root-pipeline-requires-exact-execution-release')
    need(raw_packet==canonical(packet)+b'\n','successor-exact-canonical-launch-packet')
    ops=SuccessorOps(packet,raw_packet,evidence)
    try:return SuccessorKeeper(packet,sha(raw_packet),ops).serve(next_command)
    except BaseException:
        if ops.raw_hold is not None:ops.quarantine_wait()
        raise
