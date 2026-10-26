"""Functional OS source/private fixtures only; no security testing."""
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase = load('phase', 'phase_bootstrap.SOURCE-ONLY.py')
k = load('keeper', 'keeper_protocol.SOURCE-ONLY.py')
fixed = load('fixed', 'fixed_root_custody_standby.WITH-OUTER.SOURCE-ONLY.py')
p = phase.adoption()


def packet():
    return dict(schema='mckernel.current290.held-custody-keeper-source.v1',
                mode='STANDBY_ONLY_UNTIL_SEPARATE_RETIREMENT_AUTH', author='/root',
                old_actor=p.ROOT_ACTOR, original_outer_caller=dict(pid=1060802, starttime='80309549'),
                tool_session_id=65524, old_release_sha256=p.RELEASE_SHA,
                old_plan_canonical_sha256=p.PLAN_CANONICAL_SHA,
                fixed_cutoffs=[k.WALL_CUTOFF, k.MONOTONIC_CUTOFF, k.BOOT_CUTOFF],
                standby_seconds=60, collector_reference=None, retirement_auth=None,
                execution_release=dict(status='PASS_EXECUTION_RELEASE', reviewer='fixture-reviewer', evidence_sha256='f'*64))


def receipt():
    return dict(target=p.ROOT_ACTOR, pidfd_exit_ready=True,
                sudo_join=dict(pid=1060803, starttime='80309553', pgid=1060803, returncode=137,
                               direct_child_joined=True, closed_streams=True, group_absent=True),
                outer_caller=dict(pid=1060802, starttime='80309549'), tool_session_id=65524,
                original_outer_tool_joined=True, original_outer_caller_joined=True,
                protected_state_unchanged=True, only_old_root_actor_signalled=True)


class FakeCustody:
    def __init__(self, ops):
        self.ops, self.verified, self.error, self.proof = ops, True, None, {'fixture_only': True}
        self.pidfd, self.fd = 77, 88
        self.closed = False
    def verify_old_alive(self):
        self.ops.events.append('old-alive')
        k.need(not self.closed and self.ops.old_alive, 'fixture-old-not-alive')
    def verify_held_after_exit(self):
        self.ops.events.append('held-after-exit')
        k.need(not self.closed and not self.ops.old_alive, 'fixture-postexit-held')
    def close_new_copy_while_old_alive(self):
        self.verify_old_alive()
        self.ops.events.append('close-new-only')
        self.closed = True


class FakeOps:
    def __init__(self, failure=None):
        self.events, self.clock, self.old_alive = [], 0, True
        self.failure = failure
        self.custody = FakeCustody(self)
    def now(self): return self.clock
    def clock_check(self): self.events.append('clock')
    def capture_process(self, *args): self.events.append('process-capture')
    def acquire(self):
        self.events.append('getfd')
        return self.custody
    def publish(self, name, value):
        self.events.append(name)
        if self.failure == name: raise RuntimeError('fixture-evidence-failure')
    def authorize_retirement(self, *args):
        self.events.append('authorize-separate-retirement')
        if self.failure == 'authorization': raise k.Refusal('fixture-root-auth-missing')
    def configure_phase(self):
        self.events.append('full-old-configure-with-common-alias')
        if self.failure == 'configure': raise k.Refusal('fixture-normal-typed-source-refusal')
        return {'fixture_configured': True}
    def sole_pidfd_sigkill(self, pidfd):
        self.events.append('pidfd-signal')
        self.old_alive = False
        if self.failure == 'signal': raise OSError('fixture-uncertain-signal')
    def positive_pidfd_exit(self, pidfd):
        self.events.append('positive-pidfd-exit')
        if self.failure == 'exit': return dict(pidfd_exit_ready=False)
        return dict(pidfd_exit_ready=True)
    def authorize_join_receipt(self, value, launch, raw_sha):
        self.events.append('authenticate-original-joins')
        phase.require_retirement_and_joins(p, value, launch)
        return value
    def bootstrap(self, configured, custody, value, launch):
        self.events.append('bootstrap')
        if self.failure == 'bootstrap': raise k.Refusal('fixture-bootstrap-error')
        return types.SimpleNamespace(remaining=(1,))


class KeeperTests(unittest.TestCase):
    def start(self, failure=None):
        ops = FakeOps(failure)
        keeper = k.Keeper(packet(), 'a'*64, ops)
        self.assertEqual(keeper.start(), 'VERIFIED_STANDBY')
        return keeper, ops

    def test_real_frozen_identities_exact_credential_domains(self):
        raw = fixed.IDENTITIES.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), fixed.IDENTITIES_SHA)
        data = json.loads(raw)
        rows = {row['pid']: row for row in data['processes']}
        for pid, uid in ((1060802, 1000), (1060803, 0), (1060806, 0)):
            row = rows[pid]
            def read_bytes(path, row=row):
                if path.name == 'stat': return row['stat_raw_utf8'].encode()
                if path.name == 'cmdline': return bytes.fromhex(row['cmdline_raw_hex'])
                raise AssertionError(str(path))
            def read_text(path, row=row):
                if path.name == 'status': return row['status_raw_utf8']
                raise AssertionError(str(path))
            with mock.patch.object(Path, 'read_bytes', read_bytes), mock.patch.object(Path, 'read_text', read_text):
                answer = fixed.process(p, pid, row['starttime'], row['ppid'], row['pgid'], uid, uid)
                self.assertEqual(answer['credentials'], {'Uid': [str(uid)]*4, 'Gid': [str(uid)]*4})
                if uid == 0:
                    with self.assertRaises(p.Refusal):
                        fixed.process(p, pid, row['starttime'], expected_uid=1000, expected_gid=1000)

    def test_stopped_or_traced_exact_actor_refused_from_retained_stat(self):
        data = json.loads(fixed.IDENTITIES.read_bytes())
        row = next(r for r in data['processes'] if r['pid'] == fixed.PID)
        for state in ('T', 't'):
            raw = row['stat_raw_utf8'].replace(') S ', ') ' + state + ' ', 1).encode()
            with self.subTest(state=state), mock.patch.object(Path, 'read_bytes', return_value=raw):
                with self.assertRaises(p.Refusal):
                    fixed.process(p, fixed.PID, fixed.START)

    def test_standby_capture_precedes_getfd(self):
        keeper, ops = self.start()
        self.assertLess(ops.events.index('process-capture'), ops.events.index('getfd'))
        self.assertLess(ops.events.index('old-alive'), ops.events.index('HELD-CUSTODY.json'))
        self.assertFalse(keeper.retirement_intent_consumed)

    def test_deadline_closes_only_new_copy_with_live_old_actor(self):
        keeper, ops = self.start()
        ops.clock = 60
        self.assertEqual(keeper.expire_before_retirement(), 'CLOSED_NEW_COPY_OLD_ACTOR_RETAINED')
        self.assertTrue(ops.custody.closed)
        self.assertTrue(ops.old_alive)
        self.assertNotIn('pidfd-signal', ops.events)

    def test_deadline_unknown_old_actor_retains_copy(self):
        keeper, ops = self.start()
        ops.old_alive, ops.clock = False, 60
        self.assertEqual(keeper.expire_before_retirement(), 'HELD_QUARANTINE')
        self.assertFalse(ops.custody.closed)

    def test_separate_auth_required_before_configure_and_signal(self):
        keeper, ops = self.start('authorization')
        with self.assertRaises(k.Refusal): keeper.retire({})
        self.assertNotIn('pidfd-signal', ops.events)
        self.assertNotIn('full-old-configure-with-common-alias', ops.events)
        self.assertFalse(keeper.retirement_intent_consumed)

    def test_configure_failure_preserves_actor_and_copy(self):
        keeper, ops = self.start('configure')
        with self.assertRaises(k.Refusal): keeper.retire({})
        self.assertTrue(ops.old_alive)
        self.assertFalse(ops.custody.closed)
        self.assertFalse(keeper.retirement_intent_consumed)

    def test_custody_and_configure_precede_budget_then_signal(self):
        keeper, ops = self.start()
        self.assertEqual(keeper.retire({}), 'OLD_ROOT_EXITED_AWAITING_ORIGINAL_JOINS')
        sequence = ['HELD-CUSTODY.json', 'authorize-separate-retirement', 'full-old-configure-with-common-alias',
                    'RETIREMENT-BUDGET-CONSUMED.json', 'pidfd-signal', 'positive-pidfd-exit', 'held-after-exit']
        indices = [ops.events.index(event) for event in sequence]
        self.assertEqual(indices, sorted(indices))
        self.assertFalse(ops.custody.closed)
        with self.assertRaises(k.Refusal): keeper.expire_before_retirement()

    def test_uncertain_signal_no_retry_or_close(self):
        keeper, ops = self.start('signal')
        self.assertEqual(keeper.retire({}), 'HELD_QUARANTINE')
        self.assertTrue(keeper.retirement_intent_consumed)
        self.assertFalse(ops.custody.closed)
        with self.assertRaises(k.Refusal): keeper.retire({})
        self.assertEqual(ops.events.count('pidfd-signal'), 1)

    def test_durable_intent_failure_consumes_budget_and_keeps_copy(self):
        keeper, ops = self.start('RETIREMENT-BUDGET-CONSUMED.json')
        self.assertEqual(keeper.retire({}), 'HELD_QUARANTINE')
        self.assertTrue(keeper.retirement_intent_consumed)
        self.assertFalse(keeper.signal_call_attempted)
        self.assertNotIn('pidfd-signal', ops.events)
        self.assertFalse(ops.custody.closed)

    def test_after_configure_deadline_prevents_signal(self):
        keeper, ops = self.start()
        original = ops.configure_phase
        def long_configure():
            value = original()
            ops.clock = 61
            return value
        ops.configure_phase = long_configure
        with self.assertRaises(k.Refusal): keeper.retire({})
        self.assertFalse(keeper.retirement_intent_consumed)
        self.assertFalse(keeper.signal_call_attempted)
        self.assertNotIn('pidfd-signal', ops.events)
        self.assertFalse(ops.custody.closed)

    def test_immediate_signal_deadline_failure_keeps_copy_without_signal(self):
        keeper, ops = self.start()
        original = ops.publish
        def publish(name, value):
            original(name, value)
            if name == 'RETIREMENT-BUDGET-CONSUMED.json': ops.clock = 61
        ops.publish = publish
        self.assertEqual(keeper.retire({}), 'HELD_QUARANTINE')
        self.assertTrue(keeper.retirement_intent_consumed)
        self.assertFalse(keeper.signal_call_attempted)
        self.assertNotIn('pidfd-signal', ops.events)
        self.assertFalse(ops.custody.closed)

    def test_absent_positive_exit_blocks_bootstrap(self):
        keeper, ops = self.start('exit')
        self.assertEqual(keeper.retire({}), 'HELD_QUARANTINE')
        self.assertNotIn('bootstrap', ops.events)
        self.assertFalse(ops.custody.closed)

    def test_missing_original_join_blocks_bootstrap_and_keeps_copy(self):
        keeper, ops = self.start()
        keeper.retire({})
        value = receipt()
        value['original_outer_tool_joined'] = False
        self.assertEqual(keeper.adopt_after_joins(value), 'HELD_QUARANTINE')
        self.assertNotIn('bootstrap', ops.events)
        self.assertFalse(ops.custody.closed)

    def test_positive_original_joins_unlock_only_bootstrap(self):
        keeper, ops = self.start()
        keeper.retire({})
        self.assertEqual(keeper.adopt_after_joins(receipt()), 'PHASE_BOOTSTRAP_READY_CUSTODY_HELD')
        self.assertEqual(keeper.tx.remaining, (1,))
        self.assertFalse(ops.custody.closed)

    def test_bootstrap_failure_keeps_copy(self):
        keeper, ops = self.start('bootstrap')
        keeper.retire({})
        self.assertEqual(keeper.adopt_after_joins(receipt()), 'HELD_QUARANTINE')
        self.assertFalse(ops.custody.closed)

    def test_fixed_window_outer_birth_and_unbound_collector(self):
        for key, value in [('fixed_cutoffs', [0,0,0]), ('original_outer_caller', dict(pid=1060802,starttime='wrong')),
                           ('collector_reference', {'unreviewed': True})]:
            with self.subTest(key=key):
                bad = packet(); bad[key] = value
                with self.assertRaises(k.Refusal): k.require_launch(bad, 'a'*64)

    def test_original_process_collector_preserved_but_never_called_by_bootstrap(self):
        engine = phase.original_engine(p)
        self.assertFalse(engine.CENSUS_DELTA_BOUND)
        self.assertEqual(engine.process_absent.__code__.co_filename, str(p.SOURCE))
        self.assertEqual(engine.run_privileged.__code__.co_filename, str(p.SOURCE))
        # No engine census/process call occurs anywhere in source bootstrap; the
        # source-only run override refuses until a separately released mutator.
        self.assertNotIn('census', phase.bootstrap_held_transaction.__code__.co_names)


class ArchiveAliasTests(unittest.TestCase):
    def fixture(self, configure_failure=False):
        tmp = tempfile.TemporaryDirectory(prefix='phase-alias-private-', dir=HERE)
        root = Path(tmp.name)
        engine = phase.original_engine(p)
        engine.ATTEMPT = root / 'common'
        engine.PLAN, engine.JOURNAL, engine.QUARANTINE = [root / name for name in ('plan','journal','quarantine')]
        archive = root / 'common.archive'
        for path, raw in ((engine.PLAN,b'original-plan'), (engine.JOURNAL,b'original-journal-four-events'),
                          (engine.QUARANTINE,b'original-quarantine'), (archive,b'original-common-record')):
            path.write_bytes(raw); path.chmod(0o600)
        row = engine.observe_identity(archive); row['path'] = str(engine.ATTEMPT)
        release = {'observation': {'retained_exclusions': [row, {'path':str(root/'shared')}]}}
        plan = {'records': [[str(engine.ATTEMPT),str(root),archive.name], ['shared',str(root),'shared.archive']]}
        events = []
        observe, read = engine.observe_identity, engine.read_bounded
        def configure(value, execute, dead_caller):
            events.append(('configure', execute, dead_caller))
            self.assertEqual(engine.observe_identity(engine.ATTEMPT), row)
            self.assertEqual(engine.read_bounded(engine.ATTEMPT), b'original-common-record')
            # Non-common path still uses real reader/identity; no blanket alias.
            self.assertEqual(engine.read_bounded(engine.JOURNAL), b'original-journal-four-events')
            events.extend(['source-check', 'normal-typed-check', 'current-metadata-check'])
            if configure_failure: raise engine.Refusal('fixture-original-configure-refusal')
            engine.RELEASE = value
        engine.configure = configure
        alias = phase.CompletedCommonArchiveAlias(engine, release, plan,
                        engine.PLAN.read_bytes(), engine.JOURNAL.read_bytes(), engine.QUARANTINE.read_bytes())
        return tmp, engine, alias, archive, events, observe, read

    def test_real_archive_alias_only_common_and_restores_readers(self):
        tmp, m, alias, archive, events, observe, read = self.fixture()
        try:
            before = archive.stat()
            calls = alias.configure_original()
            self.assertEqual(len(calls),2)
            self.assertIs(m.observe_identity, observe)
            self.assertIs(m.read_bounded, read)
            self.assertFalse(m.ATTEMPT.exists())
            self.assertEqual(archive.stat().st_ino,before.st_ino)
            self.assertEqual(archive.stat().st_ctime_ns,before.st_ctime_ns)
            self.assertIn('normal-typed-check',events)
            with self.assertRaises(FileNotFoundError): m.read_bounded(m.ATTEMPT)
        finally: tmp.cleanup()

    def test_original_configure_refusal_restores_readers(self):
        tmp, m, alias, archive, events, observe, read = self.fixture(True)
        try:
            with self.assertRaises(m.Refusal): alias.configure_original()
            self.assertIs(m.observe_identity,observe)
            self.assertIs(m.read_bounded,read)
            self.assertFalse(m.ATTEMPT.exists())
        finally: tmp.cleanup()

    def test_partial_state_mutations_refuse_alias(self):
        for change in ('archive','plan','journal','quarantine','common-reappeared'):
            with self.subTest(change=change):
                tmp,m,alias,archive,events,observe,read = self.fixture()
                try:
                    if change == 'archive': archive.write_bytes(b'changed')
                    elif change == 'common-reappeared': m.ATTEMPT.write_text('foreign-owner')
                    else: getattr(m, change.upper()).write_bytes(b'changed')
                    with self.assertRaises(m.Refusal): alias.configure_original()
                    self.assertEqual(events,[])
                    self.assertIs(m.observe_identity,observe)
                finally: tmp.cleanup()



class BootstrapRealFileTests(unittest.TestCase):
    def test_held_bootstrap_original_plan_and_protected_files(self):
        previous = HERE.parent / 'test_partial_quarantine_adoption.py'
        self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(),
                         'e78926f30590d87a74054f6f82071e607ddeb7799896f0e58a63e39deb9b0939')
        spec = importlib.util.spec_from_file_location('previous_private_fixture', previous)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        fixtures.HERE = HERE  # All temporary fixture writes stay in this child.
        with fixtures.ActualPrivateTransaction() as f:
            m = f.m
            tree = ast.parse(p.SOURCE.read_bytes())
            functions = {'directory', 'observe_identity', 'metadata_identity', 'metadata_inventory',
                         'require_unowned_shared_absent', 'protected_files'}
            nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
            original_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Transaction')
            method_names = {'lock', 'expected_plan', 'load_plan'}
            methods = [node for node in original_class.body if isinstance(node, ast.FunctionDef) and node.name in method_names]
            cls = ast.ClassDef(name='OriginalBootstrapMethods', bases=[], keywords=[], body=methods, decorator_list=[])
            exec(compile(ast.fix_missing_locations(ast.Module(body=nodes+[cls],type_ignores=[])),str(p.SOURCE),'exec'),m.__dict__)
            for name in method_names: setattr(m.Transaction,name,getattr(m.OriginalBootstrapMethods,name))
            def pinned(tx):
                for path, fd in ((m.ROOT,tx.fd),(m.NAMESPACE,tx.nfd)):
                    self.assertEqual((path.stat().st_dev,path.stat().st_ino),(os.fstat(fd).st_dev,os.fstat(fd).st_ino))
            m.Transaction.pinned = pinned  # Private mount/actor fixture boundary only.
            m.PROTECTED_LIMIT,m.INVENTORY_LIMIT = 1<<20,1000
            m.OWNERSHIP_CASE = None
            m.LEASE = f.ns / 'lease.absent'
            m.CANDIDATE = f.root / 'candidate'; m.CANDIDATE.mkdir(mode=0o700)
            backup = f.root / 'backup'; backup.mkdir(mode=0o700)
            m.PROTECTED = [m.observe_identity(m.TERMINAL)]
            m.RELEASE = dict(observation=dict(inventories={str(root):m.metadata_inventory(root) for root in (m.OUTPUT,m.EVIDENCE)},
                                  candidate_root=m.observe_identity(m.CANDIDATE),backup_root=m.observe_identity(backup)))
            m.UUID,m.BOOT_ID,m.OWNER_PID,m.OWNER_START = 'fixture-uuid','fixture-boot',123,'42'
            m.WAITER_PIDS = ()
            m.CONTAINER,m.CONTAINER_NAME,m.OWNER_NONCE = 'fixture-container','fixture-name','fixture-nonce'
            m.PUBLISHER_CONTRACT = {'fixture-only':'regular-file publisher'}
            m.NAMESPACE_BINDING = dict(device=f.ns.stat().st_dev,inode=f.ns.stat().st_ino,
                                      mode=f.ns.stat().st_mode,uid=os.getuid(),gid=os.getgid())
            m.NAMESPACE_ANCESTRY = [{'fixture-only':str(f.ns)}]
            m.ROOT_LOCK = f.root/'private-root.lock'; f.write(m.ROOT_LOCK,b'')
            m.ROOT_LOCK_BINDING = m.observe_identity(m.ROOT_LOCK)
            f.write(m.MUTEX,b'')
            holder = os.open(m.ROOT_LOCK,os.O_RDONLY)
            fcntl.flock(holder,fcntl.LOCK_EX|fcntl.LOCK_NB)
            duplicate = os.dup(holder)
            opened = []
            try:
                for path,key in ((m.ROOT,'chain'),(m.NAMESPACE,'namespace_chain')):
                    fd,chain=m.directory(path); os.close(fd); setattr(f.tx,key,chain)
                temporary_mutex=os.open(m.MUTEX,os.O_RDONLY)
                f.tx.mfd=temporary_mutex
                plan=f.tx.expected_plan(f.plan['sentinels'])
                os.close(temporary_mutex); f.tx.mfd=None
                plan_raw=m.canonical(plan)+b'\n'
                m.PLAN.write_bytes(plan_raw)
                m.JOURNAL.write_bytes(b'')
                rows=[]
                for event in ('before_exchange','after_exchange','release','after_release'):
                    f.tx.append(plan,rows,event,0)
                journal_raw=m.JOURNAL.read_bytes()
                original_quarantine=b'original fixture quarantine\n'
                f.write(m.QUARANTINE,original_quarantine)
                configured=dict(original_release=m.RELEASE,raw_plan=plan_raw,raw_journal=journal_raw,
                                raw_quarantine=original_quarantine)
                class Custody:
                    fd=duplicate
                    checks=0
                    def verify_held_after_exit(self_inner):
                        self_inner.checks+=1
                        meta={key:getattr(os.fstat(duplicate),key) for key in k.FIELDS}
                        p.verify_description_custody(duplicate,os.getpid(),holder,m.ROOT_LOCK,meta)
                custody=Custody()
                def archive(path,raw):
                    self.assertEqual(path.read_bytes(),raw)
                    f.write(f.root/'original-quarantine.copy',raw)
                    return dict(original_preserved=True,sha256=p.digest(raw))
                tx=phase.bootstrap_held_transaction(p,m,configured,custody,receipt(),packet(),archive)
                opened=[tx.mfd,tx.nfd,tx.fd]
                self.assertIs(tx.rfd,custody.fd)
                self.assertGreater(custody.checks,1)
                self.assertEqual(tx.original_plan,plan)
                self.assertEqual(tx.state(plan)[1],['after_release','before_exchange'])
                self.assertEqual(m.PLAN.read_bytes(),plan_raw)
                self.assertEqual(m.JOURNAL.read_bytes(),journal_raw)
                self.assertEqual(m.QUARANTINE.read_bytes(),original_quarantine)
                self.assertEqual((f.root/'original-quarantine.copy').read_bytes(),original_quarantine)
                self.assertFalse(m.ATTEMPT.exists())
                with self.assertRaises(m.Refusal): tx.run(True)
                with self.assertRaises(m.Refusal): tx.close()
                os.fstat(duplicate)  # Root-custody fixture FD remains held.
            finally:
                for fd in opened+[duplicate,holder]:
                    if fd is not None: os.close(fd)


if __name__ == '__main__':
    unittest.main(verbosity=2)
