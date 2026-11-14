"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow SOURCE composition for frozen0a67 Ops: custody acquisition/verification only.
Does not alter Keeper transitions, authorize retirement, joins, mutation or release.
"""
import hashlib
import os
from pathlib import Path
import types
import keeper_custody_successor as successor

HERE=Path(__file__).resolve().parent

def ref(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def install_custody_successor(ops,authorization):
    """Definition-only composition. Must run before acquire, under a new release.
    A pinned Root composition document plus independent exact source review is
    required. Neither document is a native execution/retirement authorization.
    """
    own=ref(Path(__file__).resolve());adapter=ref(HERE/'keeper_custody_successor.py')
    expected=dict(author='/root',decision='GRANT_EXACT_HELD_KEEPER_CUSTODY_SOURCE_COMPOSITION',
       bridge=own,adapter=adapter,custody_adapter=successor.ADAPTER,
       target=dict(pid=successor.PID,starttime=successor.START,parent=successor.PARENT,
                   pgid=successor.PGID,fd=successor.TARGET_FD,boot_id=successor.BOOT),
       lock_origin_pid=successor.LOCK_ORIGIN_PID,predecessor_launch_sha256=successor.PINS['launch'][2])
    successor.need(isinstance(authorization,dict) and set(authorization)==set(expected)|{'source_review'},'closed-custody-composition-authorization')
    successor.need(all(authorization[k]==v for k,v in expected.items()),'exact-custody-composition-binding')
    review=ops.pinned_document(authorization['source_review'])
    successor.need(review.get('decision')=='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY'
       and review.get('reviewer') not in (None,'','/root') and review.get('bridge')==own
       and review.get('adapter')==adapter,'independent-custody-composition-source-review')
    successor.need(ops.packet.get('successor_custody_adapter')==successor.ADAPTER
       and ops.packet.get('custody_successor_composition')==authorization,'packet-custody-composition-binding')
    successor.need(ops.raw_hold is None and not getattr(ops,'_HELD_KEEPER_CUSTODY_SUCCESSOR',False),'custody-composition-before-copy-once')
    successor.authenticate_predecessor()
    class Custody:
        def __init__(self,hold):
            self.module,self.p=successor,successor.adoption()
            self.fd,self.pidfd=hold.fd,hold.pidfd
            self.verified,self.error,self.proof=hold.verified,hold.error,hold.proof
            self.metadata=successor.metadata(os.fstat(self.fd));self.closed=False
        def verify_old_alive(self):
            successor.need(not self.closed and self.verified,'successor-private-copy-not-verified-held')
            before=successor.actor_binding(self.p);successor.live_pidfd(self.p,self.pidfd)
            successor.verify_description_custody(self.fd,successor.PID,successor.TARGET_FD,self.p.ROOT_MUTEX,self.metadata)
            successor.live_pidfd(self.p,self.pidfd)
            successor.need(successor.actor_binding(self.p)==before,'successor-current-custodian-raced')
            return True
        def verify_held_after_exit(self):
            successor.need(not self.closed and self.verified,'successor-copy-not-verified-held-after-exit')
            return successor.verify_held_after_exit(self.fd,self.pidfd,self.metadata,self.p.ROOT_MUTEX)
        def close_new_copy_while_old_alive(self):
            self.verify_old_alive();os.close(self.pidfd);os.close(self.fd);self.closed=True
    def acquire(instance):
        raw=successor.acquire_exact_standby();instance.raw_hold=raw
        try:return Custody(raw)
        except BaseException as error:
            # No allocation/import/I/O precedes retention of the raw copy.
            # Exception representation itself cannot grant permission to close.
            return types.SimpleNamespace(fd=raw.fd,pidfd=raw.pidfd,verified=False,
                                         error=type(error).__name__+': '+str(error),proof=None)
    ops.custody_module=successor
    ops.acquire=types.MethodType(acquire,ops)
    manifest=dict(schema='mckernel.current290.held-keeper-custody-source-composition.v1',
        bridge=own,adapter=adapter,lock_origin_pid=successor.LOCK_ORIGIN_PID,
        current_custodian=expected['target'],source_review=authorization['source_review'],
        runtime_execution_authority=False,retirement_authority=False,mutation_authority=False,
        original_actor_retirement_replayed=False)
    ops._HELD_KEEPER_CUSTODY_SUCCESSOR=manifest
    return manifest

if __name__=='__main__':raise SystemExit('SOURCE ONLY: no native runtime launch authority')
