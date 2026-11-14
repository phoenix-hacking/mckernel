"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

UNRELEASED sourceable phase bootstrap. Unchanged e49 configure and Transaction
predicates remain the consumers. A completed common record may be read only
through an explicit, independently authenticated archive alias DURING configure.
No cleanup/run entrypoint or root invocation is provided by this module.
"""
import hashlib
import json
import os
from pathlib import Path
import types

PARENT = Path(__file__).resolve().parent.parent
ADOPTION_SOURCE = PARENT / 'partial_quarantine_adoption.py'
ADOPTION_SHA = '57722eab94b8494c2423cf9a161ff43ed2948018fa0ddc8ad59f91cd9d9968aa'
COLLECTOR_REFERENCE = dict(path='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-correction-source-1/census-runtime-bridge-source-1/census_runtime_bridge.py', bytes=8758, sha256='c9af3506af824af58c599a2aa8d7a1aae30b680a25c4bcc5ca87b8bcd1d20a2a')


def adoption():
    raw = ADOPTION_SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ADOPTION_SHA:
        raise RuntimeError('partial-adoption-source-differs')
    module = types.ModuleType('_frozen_partial_adoption')
    module.__file__ = str(ADOPTION_SOURCE)
    exec(compile(raw, str(ADOPTION_SOURCE), 'exec'), module.__dict__)
    return module


def original_engine(p):
    """Definitions execute; this bootstrap never invokes old main or collector."""
    raw = p.pinned_bytes(p.SOURCE, p.SOURCE_SHA, 128910)
    module = types.ModuleType('_unchanged_e49_phase_adoption')
    module.__file__ = str(p.SOURCE)  # Original source/git predicates read original bytes.
    exec(compile(raw, str(p.SOURCE), 'exec'), module.__dict__)
    # Keep original process_absent/run_privileged intact for the closed reviewed
    # diagnostic delta installer. This bootstrap never invokes census/run; any
    # future mutator must first bind the separate corrected collector authority.
    module.CENSUS_DELTA_BOUND = False
    return module


class CompletedCommonArchiveAlias:
    """One completed slot, explicit old row and archive; no general path mapper."""
    def __init__(self, engine, release, plan, raw_plan, raw_journal, raw_quarantine):
        self.m, self.release, self.plan = engine, release, plan
        self.raw_plan, self.raw_journal, self.raw_quarantine = raw_plan, raw_journal, raw_quarantine
        self.observe = engine.observe_identity
        self.read = engine.read_bounded
        records = release['observation']['retained_exclusions']
        engine_refusal = engine.Refusal
        if len(records) != 2 or len(plan['records']) != 2:
            raise engine_refusal('phase-alias-two-original-records-required')
        self.row = records[0]
        self.active = engine.ATTEMPT
        self.archive = Path(plan['records'][0][1]) / plan['records'][0][2]
        if self.row['path'] != str(self.active) or self.archive.parent != self.active.parent:
            raise engine_refusal('phase-alias-common-only-fixed-parent')
        self.calls = []

    def check(self):
        m = self.m
        if (os.path.lexists(self.active) or self.read(m.PLAN) != self.raw_plan
                or self.read(m.JOURNAL) != self.raw_journal
                or self.read(m.QUARANTINE) != self.raw_quarantine):
            raise m.Refusal('phase-alias-prior-state-raced')
        archived = self.observe(self.archive)
        expected = dict(self.row, path=str(self.archive))
        if archived != expected:
            raise m.Refusal('phase-alias-original-archived-record-differs')
        if self.read(self.archive) != self.read_expected_record():
            raise m.Refusal('phase-alias-archive-bytes-differ')
        if os.path.lexists(self.active):
            raise m.Refusal('phase-alias-common-active-reappeared')

    def read_expected_record(self):
        raw = self.read(self.archive)
        if len(raw) != self.row['size'] or hashlib.sha256(raw).hexdigest() != self.row['sha256']:
            raise self.m.Refusal('phase-alias-original-bytes-binding')
        return raw

    def observe_common(self, path):
        if path != self.active:
            return self.observe(path)
        self.check()
        self.calls.append(('observe_identity', str(path), str(self.archive)))
        # This return is an explicit logical old-release record view, NOT a
        # claim that the released original active pathname exists currently.
        return dict(self.row)

    def read_common(self, path, *args, **kwargs):
        if path != self.active:
            return self.read(path, *args, **kwargs)
        self.check()
        raw = self.read(self.archive, *args, **kwargs)
        if len(raw) != self.row['size'] or hashlib.sha256(raw).hexdigest() != self.row['sha256']:
            raise self.m.Refusal('phase-alias-record-read-binding')
        self.calls.append(('read_bounded', str(path), str(self.archive)))
        return raw

    def configure_original(self):
        """The one narrow alias is installed only for the unchanged configure."""
        m = self.m
        self.check()
        if m.observe_identity != self.observe or m.read_bounded != self.read:
            raise m.Refusal('phase-alias-engine-already-overridden')
        try:
            m.observe_identity, m.read_bounded = self.observe_common, self.read_common
            m.configure(self.release, execute=False, dead_caller=True)
        finally:
            m.observe_identity, m.read_bounded = self.observe, self.read
        self.check()
        if m.RELEASE is not self.release or m.canonical(m.RELEASE) != m.canonical(self.release):
            raise m.Refusal('phase-alias-old-release-provenance-lost')
        return tuple(self.calls)


def configure_phase_aware(p, m):
    """Full old configure/source/normal-typed checks run on actual live inputs.

    This function is defined but UNRUN against production in this source stage.
    """
    proof = p.authenticate_retained_snapshot()
    old_release_raw = p.pinned_bytes(p.PREPARATION / 'RELEASE.PASS_EXECUTION_RELEASE.json', p.RELEASE_SHA, 241402)
    release = p.strict(old_release_raw)
    plan_raw = p.pinned_bytes(p.SNAPSHOT / 'PLAN.json', p.PLAN_SHA, 15316)
    journal_raw = p.pinned_bytes(p.SNAPSHOT / 'JOURNAL.jsonl', p.JOURNAL_SHA, 1245)
    quarantine_raw = p.pinned_bytes(p.SNAPSHOT / 'QUARANTINE.json', p.QUARANTINE_SHA, 208)
    alias = CompletedCommonArchiveAlias(m, release, p.strict(plan_raw), plan_raw, journal_raw, quarantine_raw)
    used = alias.configure_original()
    return dict(proof=proof, plan=p.strict(plan_raw), raw_plan=plan_raw,
                raw_journal=journal_raw, raw_quarantine=quarantine_raw,
                original_release=release, common_alias_calls=used)



def bind_diagnostic_census(p, m, authorization):
    """Explicit NEW diagnostic authority; old release/plan are never rewritten.

    Call only after original full configure restored its two temporary common
    readers. The frozen bridge validates baseline context and changes exactly
    PROC_CODE/root_command/validate_process_report plus its additive manifest.
    """
    ref = COLLECTOR_REFERENCE
    raw = p.pinned_bytes(Path(ref['path']), ref['sha256'], ref['bytes'])
    bridge = types.ModuleType('_exact_new_census_runtime_bridge')
    bridge.__file__ = ref['path']
    exec(compile(raw, ref['path'], 'exec'), bridge.__dict__)
    release_before = m.RELEASE
    manifest = bridge.install_census_delta(m, authorization)
    if m.RELEASE is not release_before or p.digest(m.canonical(m.RELEASE)) != p.RELEASE_CANONICAL_SHA:
        raise m.Refusal('diagnostic-delta-old-release-provenance-lost')
    return manifest


def require_retirement_and_joins(p, receipt, launch):
    """Source protocol requires real pidfd exit AND authenticated creator joins."""
    expected_outer = launch.get('original_outer_caller')
    p.need(expected_outer == dict(pid=1060802, starttime='80309549'),
           'positive-original-outer-caller-birth-required')
    p.need(receipt.get('target') == p.ROOT_ACTOR and receipt.get('pidfd_exit_ready') is True,
           'positive-original-root-pidfd-exit-required')
    sudo = receipt.get('sudo_join', {})
    p.need(sudo.get('pid') == 1060803 and sudo.get('starttime') == '80309553'
           and sudo.get('pgid') == 1060803 and type(sudo.get('returncode')) is int
           and all(sudo.get(k) is True for k in ('direct_child_joined', 'closed_streams', 'group_absent')),
           'positive-original-sudo-creator-join-required')
    p.need(receipt.get('outer_caller') == expected_outer and receipt.get('tool_session_id') == 65524
           and receipt.get('original_outer_tool_joined') is True
           and receipt.get('original_outer_caller_joined') is True,
           'positive-original-outer-caller-tool-join-required')
    p.need(receipt.get('protected_state_unchanged') is True and receipt.get('only_old_root_actor_signalled') is True,
           'positive-retirement-scope-and-protected-state-required')
    return True


def bootstrap_held_transaction(p, m, configured, custody, receipt, launch, archive_original_quarantine):
    """Construct an original-predicate Tx from genuine retained held custody.

    No original prepare/run/close executes. The returned Tx has no runnable
    adoption entrypoint: remaining shared mutation is a separate future module.
    The caller/keeper retains custody on ALL errors and must never auto-close it.
    """
    require_retirement_and_joins(p, receipt, launch)
    custody.verify_held_after_exit()
    if m.RELEASE is not configured['original_release']:
        raise m.Refusal('bootstrap-old-release-object-differs')
    # Keep the original quarantine in place; durable additive archive precedes
    # transaction adoption. This is not a quarantine unlink/rename/clear.
    archived = archive_original_quarantine(m.QUARANTINE, configured['raw_quarantine'])
    if not archived or archived.get('original_preserved') is not True:
        raise m.Refusal('bootstrap-original-quarantine-archive-required')
    base = m.Transaction
    class HeldTransaction(base):
        def __init__(self):
            raise m.Refusal('bootstrap-explicit-construction-only')
        def pinned(self):
            custody.verify_held_after_exit()
            return base.pinned(self)
        def close(self):
            # Release of the sole retained root description belongs to a later
            # independently reviewed terminal physical acceptance operation.
            raise m.Refusal('bootstrap-keeper-custody-must-remain-held')
        def run(self, execute):
            raise m.Refusal('remaining-shared-mutator-not-released-or-implemented-here')
    tx = object.__new__(HeldTransaction)
    tx.fd = tx.nfd = tx.mfd = None
    tx.rfd = custody.fd  # Exact held description; no independent open/acquisition.
    tx.root_locked, tx.root_lock_inherited = True, False
    tx.mutation_started = True
    try:
        tx.fd, tx.chain = m.directory(m.ROOT)
        tx.nfd, tx.namespace_chain = m.directory(m.NAMESPACE)
        tx.pinned()
        tx.lock(False)  # Original generation-bound mutex validation/acquisition.
        m.protected_files()
        plan = tx.load_plan()  # Original expected_plan includes OLD canonical release.
        if m.canonical(plan) + b'\n' != configured['raw_plan']:
            raise m.Refusal('bootstrap-original-plan-provenance')
        if p.require_partial_phase(tx, plan, configured['raw_plan'], configured['raw_journal']) != (1,):
            raise m.Refusal('bootstrap-shared-only-phase')
        tx.adoption_archive = archived
        tx.original_plan = plan
        return tx
    except BaseException:
        # These newly opened auxiliary descriptors own no permanent root lock.
        # Root custody remains in the keeper. No tx.close() is invoked.
        for name in ('mfd', 'nfd', 'fd'):
            fd = getattr(tx, name)
            if fd is not None:
                os.close(fd)
                setattr(tx, name, None)
        raise


if __name__ == '__main__':
    raise SystemExit('SOURCE ONLY: no root runtime release or shared mutator entrypoint')
