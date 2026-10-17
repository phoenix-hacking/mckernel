"""Image-only joins and reused native transaction; no live inputs or children."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'scripts/native_exact_scratch22_authority3_image_cleanup.py'
BASE = ROOT / 'scripts/native_exact_scratch22_authority3_terminal_cleanup.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImageCleanupTests(unittest.TestCase):
    def setUp(self):
        self.m = load(SOURCE, 'image_cleanup_fixture')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.m.ROOT = Path(self.temp.name)
        m = self.m
        for name in ('OUTPUT', 'EVIDENCE', 'REQUEST', 'LEASE', 'ATTEMPT', 'SHARED'):
            setattr(m, name, m.ROOT / name.lower())
        self.request = {'schema': 'mckernel.native-exact-mckernel-image-container-request.v1',
                        'candidate_sha': m.IMAGE_CANDIDATE, 'ihk_sha': 'b' * 40,
                        'image_id': 'sha256:' + 'c' * 64, 'jobs': 4, 'timeout': 100,
                        'work_root': str(m.OUTPUT), 'owner_evidence_root': str(m.EVIDENCE),
                        'output_root': str(m.OUTPUT / 'output'), 'evidence_root': str(m.OUTPUT / 'evidence'),
                        'attempt_root': str(m.EVIDENCE / 'attempt'), 'lease_path': str(m.LEASE),
                        'common_exclusion_path': str(m.ATTEMPT),
                        'source_root': str(m.ROOT / 'source'), 'backup_root': str(m.ROOT / 'backup'),
                        'toolchain_roots': [{'host_path': str(m.ROOT / 'native'), 'container_path': '/out', 'inventory': {}},
                                            {'host_path': str(m.ROOT / 'nightly'), 'container_path': '/nightly', 'inventory': {}}]}
        for key in ('source_manifest', 'toolchain_manifest', 'driver_path', 'provenance_path', 'host_owner_path'):
            self.request[key] = str(m.ROOT / key)
        self.target = dict(m.KNOWN_TARGET, container_id='d' * 64,
                           container_name='mckernel-image-' + 'e' * 32, owner_nonce='f' * 32,
                           image_id=self.request['image_id'], exit_code=0)

    def test_fresh_namespace_unknown_terminal_and_known_owner_binding(self):
        m = load(SOURCE, 'image_cleanup_unconfigured')
        self.assertEqual(m.REQUEST_SHA, '62d4f5928c11660ff78634b4809952f482427d8978bd8f348e74f923ac8889d6')
        self.assertEqual(m.KNOWN_TARGET, {'owner_pid': 409807, 'owner_starttime': '1912441'})
        self.assertEqual(m.WAITER_PIDS, (409807, 411284, 411296, 411308, 411320, 411382, 414643, 414655, 415269))
        for name in ('CANDIDATE', 'ROOT_TERMINAL', 'CONTAINER', 'CONTAINER_NAME', 'OWNER_NONCE',
                     'OWNER_PID', 'OWNER_START', 'EXPECTED_EXIT', 'DEVICE', 'BOOT_ID', 'RELEASE'):
            self.assertIsNone(getattr(m, name))
        self.assertIn('942c927b-scratch22-authority3-image1', m.REQUEST.name)
        self.assertEqual(m.ATTEMPT.name, 'native-exact-candidate-operational-exclusion-scratch18-image-1.json')
        self.assertEqual(m.SHARED.name, 'mckernel-heavy-operation.lock')
        m.validate_attempt_binding(self.target, {'path': str(m.REQUEST), 'sha256': m.REQUEST_SHA})
        for key, value in (('owner_pid', True), ('owner_pid', 1), ('owner_starttime', 1912441),
                           ('container_name', 'mckernel-exact-' + 'e' * 32), ('owner_nonce', 'unknown')):
            changed = dict(self.target); changed[key] = value
            with self.assertRaises(m.Refusal):
                m.validate_attempt_binding(changed, {'path': str(m.REQUEST), 'sha256': m.REQUEST_SHA})
        with self.assertRaises(m.Refusal):
            m.validate_attempt_binding(self.target, {'path': str(m.REQUEST), 'sha256': '0' * 64})
        with mock.patch.object(m.os, 'open') as opened, self.assertRaises(m.Refusal): m.recover()
        opened.assert_not_called()

    def test_image_namespace_command_and_sole_work_rw_mount(self):
        m = self.m
        self.assertEqual(m.image_request_binding(self.request), Path(self.request['source_root']))
        command, mounts = m.image_layout(self.request)
        self.assertEqual([row for row in mounts if row[3]], [('/work', str(m.OUTPUT), 'bind', True)])
        self.assertEqual(command[-4:], ['--jobs', '4', '--timeout', '100'])
        for key in ('work_root', 'output_root', 'evidence_root', 'attempt_root', 'lease_path',
                    'common_exclusion_path', 'owner_evidence_root', 'candidate_sha', 'source_root'):
            changed = dict(self.request); changed[key] = '/old-namespace'
            with self.subTest(key=key), self.assertRaises(m.Refusal): m.image_request_binding(changed)
        changed = copy.deepcopy(self.request); changed['toolchain_roots'][1]['container_path'] = '/out'
        with self.assertRaises(m.Refusal): m.image_layout(changed)

    def test_common_and_shared_use_distinct_exact_encoding_and_inode_fields(self):
        m = self.m
        row = {'device': 11, 'inode': 12}
        for path in (m.ATTEMPT, m.SHARED):
            common = path == m.ATTEMPT
            record = {'schema': 'mckernel.native-exact-operational-exclusion.v1' if common else 'mckernel.heavy-operation.v1',
                      'pid': self.target['owner_pid'], 'starttime': self.target['owner_starttime'],
                      'boot_id': 'fresh', 'dev' if common else 'device': 11, 'inode': 12,
                      'request_sha256': m.digest(json.dumps(self.request, sort_keys=True).encode()) if common else
                      m.digest(m.canonical(self.request))}
            if not common: record['kind'] = 'image'
            m.image_record_binding(path, row, record, self.request, self.target, 'fresh')
            for key, value in (('request_sha256', '0' * 64), ('inode', 13), ('pid', True),
                               ('boot_id', 'stale'), ('schema', 'wrong')):
                changed = dict(record); changed[key] = value
                with self.assertRaises(m.Refusal):
                    m.image_record_binding(path, row, changed, self.request, self.target, 'fresh')
            changed = dict(record); changed['request_sha256'] = m.digest(m.canonical(self.request)) if common else m.digest(json.dumps(self.request, sort_keys=True).encode())
            with self.assertRaises(m.Refusal):
                m.image_record_binding(path, row, changed, self.request, self.target, 'fresh')

    def test_positive_receipt_guard_and_full_mount_records_are_bound(self):
        m = self.m
        item = {'Id': self.target['container_id'], 'Mounts': [{'Destination': '/a', 'RW': False},
                                                          {'Destination': '/b', 'RW': True}]}
        receipt = dict(self.target, schema='mckernel.native-exact-mckernel-image-container-receipt.v1',
                       candidate_sha=m.IMAGE_CANDIDATE, status='PASS', retired=True,
                       cleanup_separately_required=True, terminal_container_retained=True,
                       terminal_container_info=copy.deepcopy(item))
        guard = dict(owner_status='PASS', owner_receipt_sha256='a' * 64, container_id=self.target['container_id'],
                     retired=True, retained_for_separate_cleanup=True, interrupted_signal=None)
        item['Mounts'].reverse()
        m.image_receipt_binding(receipt, guard, self.target, item, 'a' * 64)
        for key, value in (('retired', False), ('client_retirement_unproven', True),
                           ('exit_code', True), ('owner_nonce', 'wrong')):
            changed = dict(receipt); changed[key] = value
            with self.assertRaises(m.Refusal): m.image_receipt_binding(changed, guard, self.target, item, 'a' * 64)
        for key, value in (('retired', 1), ('interrupted_signal', 15), ('owner_receipt_sha256', '0' * 64)):
            changed = dict(guard); changed[key] = value
            with self.assertRaises(m.Refusal): m.image_receipt_binding(receipt, changed, self.target, item, 'a' * 64)
        changed = copy.deepcopy(item); changed['Mounts'][0]['RW'] = False
        with self.assertRaises(m.Refusal): m.image_receipt_binding(receipt, guard, self.target, changed, 'a' * 64)

    def test_live_census_rejects_every_historical_client_descendant(self):
        m = self.m
        m.BOOT_ID = 'fixture-boot'
        m.OWNER_PID = 409807
        for pid in m.WAITER_PIDS:
            report = dict(schema='scratch22-authority3-image.proc.v1', uid=0, boot_id=m.BOOT_ID,
                          challenge='fresh', caller=[42, '99'], publishers=[],
                          snapshots=[[[1, 0, '1'], [42, 1, '99'], [999, pid, '12']],
                                     [[1, 0, '1'], [42, 1, '99'], [1001, 999, '13']]])
            with self.subTest(client=pid), self.assertRaises(m.Refusal):
                m.validate_process_report(report, 'fresh', [42, '99'])

    def test_recovery_consumer_requires_distinct_proof_not_owner_status(self):
        with self.assertRaises((self.m.Refusal, OSError, KeyError)):
            self.m.recovery_proof_binding({'path': '/missing/recovery-proof.json'}, {})
        tree = ast.parse(SOURCE.read_text())
        configure = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'configure')
        text = ast.unparse(configure)
        self.assertIn('exactly-one-positive-retirement-proof-required', text)
        self.assertIn('recovery_proof_binding', text)
        self.assertIn('image_receipt_binding', text)

    def test_native_transaction_signal_census_and_archival_core_unchanged(self):
        old = ast.parse(BASE.read_text())
        new = ast.parse(SOURCE.read_text().replace('scratch22-authority3-image', 'scratch22-authority3'))
        names = {'Transaction', 'recover', 'quarantine_wait', 'validate_process_report', 'census',
                 'metadata_inventory', 'observe_identity', 'rename_exchange', 'read_at', 'read_bounded'}
        def selected(tree):
            return {node.name: ast.dump(node) for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names}
        self.assertEqual(selected(old), selected(new))
        self.assertEqual(self.m.PROTECTED_LIMIT, 128 << 20)
        self.assertEqual(self.m.DOCUMENT_LIMIT, 256 << 20)
        self.assertEqual(self.m.INVENTORY_LIMIT, 400000)

    def test_actual_configure_image_positive_and_terminal_drift_refuses(self):
        m = self.m
        request, target = copy.deepcopy(self.request), dict(self.target)
        def row(path, directory=False):
            return dict(path=str(path), device=17, inode=100 + len(str(path)), mode='0o700' if directory else '0o600',
                        uid=1000, gid=1000, size=0, nlink=2 if directory else 1,
                        **({} if directory else {'sha256': m.digest(b'code')}))
        candidate, backup = row(request['source_root'], True), row(request['backup_root'], True)
        for key, identity in (('source_identity', candidate), ('backup_identity', backup)):
            request[key] = dict(path=identity['path'], dev=identity['device'], inode=identity['inode'],
                                uid=1000, gid=1000, mode=0o700, file_type=m.stat.S_IFDIR)
        joins = {'source_manifest': 'source_manifest_sha256', 'toolchain_manifest': 'toolchain_manifest_sha256',
                 'driver_path': 'driver_sha256', 'provenance_path': 'provenance_sha256',
                 'host_owner_path': 'host_owner_sha256'}
        for key in joins.values(): request[key] = m.digest(b'code')
        raw_request = m.canonical(request); m.REQUEST_SHA = m.digest(raw_request)
        command, mounts = m.image_layout(request)
        host = dict(CpusetCpus='2-5', NanoCpus=4000000000, Memory=12884901888, MemorySwap=12884901888,
                    PidsLimit=512, NetworkMode='none', IpcMode='private', ReadonlyRootfs=True,
                    Privileged=False, CapDrop=['ALL'], Init=True, SecurityOpt=['no-new-privileges'],
                    Tmpfs={'/tmp': 'rw,nodev,nosuid,size=256m'}, RestartPolicy={'MaximumRetryCount': 0, 'Name': 'no'}, AutoRemove=False)
        item = dict(Id=target['container_id'], Name='/' + target['container_name'], Image=target['image_id'],
                    Path='/usr/bin/python3', Args=command,
                    Config=dict(User='1000:1000', Entrypoint=['/usr/bin/python3'], Cmd=command,
                                Image=target['image_id'], Labels={'mckernel.owner': target['owner_nonce']}),
                    HostConfig=host, Mounts=[dict(Destination=d, Source=s, Type=t, RW=w) for d, s, t, w in mounts],
                    State=dict(Status='exited', Running=False, Paused=False, Restarting=False, OOMKilled=False,
                               Dead=False, Pid=0, ExitCode=0, Error=''))
        receipt = dict(target, schema='mckernel.native-exact-mckernel-image-container-receipt.v1',
                       candidate_sha=m.IMAGE_CANDIDATE, status='PASS', retired=True,
                       cleanup_separately_required=True, terminal_container_retained=True, terminal_container_info=item)
        m.TERMINAL = m.EVIDENCE / 'owner-receipt.json'
        proofpath = m.ROOT / ('native-image-guard-942c927b-' + 'a' * 32) / 'guard-result.json'
        guard = dict(owner_status='PASS', owner_receipt_sha256=m.digest(m.canonical(receipt)),
                     container_id=target['container_id'], retired=True,
                     retained_for_separate_cleanup=True, interrupted_signal=None)
        files = {str(m.REQUEST): raw_request, str(m.TERMINAL): m.canonical(receipt), str(proofpath): m.canonical(guard)}
        records = []
        for path in (m.ATTEMPT, m.SHARED):
            identity = row(path); records.append(identity)
            common = path == m.ATTEMPT
            owner = dict(schema='mckernel.native-exact-operational-exclusion.v1' if common else 'mckernel.heavy-operation.v1',
                         pid=target['owner_pid'], starttime=target['owner_starttime'],
                         boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', inode=identity['inode'],
                         request_sha256=m.digest(json.dumps(request, sort_keys=True).encode()) if common else m.digest(raw_request))
            owner['dev' if common else 'device'] = identity['device']
            if not common: owner['kind'] = 'image'
            files[str(path)] = m.canonical(owner)
        def identity(path):
            value = row(path, str(path) in (candidate['path'], backup['path'], str(m.ROOT)))
            if str(path) in files: value['sha256'] = m.digest(files[str(path)])
            return value
        paths = {m.REQUEST, m.TERMINAL, proofpath, m.EVIDENCE / 'attempt/container.log',
                 m.OUTPUT / 'evidence/receipt.json', m.OUTPUT / 'output/build/kernel/mckernel.img',
                 m.OUTPUT / 'evidence/artifacts/mckernel.img'} | {Path(request[key]) for key in joins}
        selected = [identity(path) for path in paths]
        records = [identity(path) for path in (m.ATTEMPT, m.SHARED)]
        obs = dict(mount=dict(target=str(m.ROOT), uuid=m.UUID, fstype='ext4', options='rw,nodev,nosuid'),
                   root=identity(m.ROOT), boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',
                   root_lock=dict(path=str(m.ROOT_LOCK), device=27, inode=4, uid=0, gid=0, mode='0o644',
                                  nlink=1, size=0, sha256=m.digest(b'')),
                   request=identity(m.REQUEST), target=target, container_inspect=item,
                   retained_exclusions=records, request_lease_absent=True,
                   inventories={str(p): [dict(path=str(p), inode=500, nlink=2)] for p in (m.OUTPUT, m.EVIDENCE)},
                   candidate_root=candidate, candidate_commit=m.IMAGE_CANDIDATE, candidate_tree='b' * 40,
                   selected_files=selected, backup_root=backup, guard_proof=identity(proofpath))
        release = dict(schema='scratch22-authority3-image.cleanup-release.v1', status='PASS_EXECUTION_RELEASE',
                       baseline_source_sha256=m.BASELINE_SOURCE_SHA, script_sha256=m.digest(b'code'),
                       tests_sha256=m.digest(b'code'), publisher_contract=m.PUBLISHER_CONTRACT,
                       author='/author', fetched_source_verified=True, git_commit='a' * 40, git_tree='b' * 40,
                       source_review=dict(status='PASS', reviewer='/reviewer', evidence_sha256='e' * 64),
                       execution_review=dict(status='PASS', reviewer='/reviewer', evidence_sha256='f' * 64),
                       observation=obs, transaction_paths=m.transaction_paths())
        def git(args, **kwargs):
            if args[3] == 'show': return b'code'
            return ((m.IMAGE_CANDIDATE if args[-1] == 'HEAD' else 'b' * 40) + '\n').encode()
        with mock.patch.object(m, 'read_bounded', side_effect=lambda path: files.get(str(path), b'code')), \
             mock.patch.object(m, 'observe_identity', side_effect=identity), \
             mock.patch.object(m.subprocess, 'check_output', side_effect=git), \
             mock.patch.object(m, 'validate_mount'), mock.patch.object(m, 'protected_files') as protected:
            m.configure(release)
            self.assertIs(m.RELEASE, release)
            protected.assert_called_once()
            item['State']['ExitCode'] = 1
            with self.assertRaisesRegex(m.Refusal, 'exact-terminal-container'): m.configure(release)
            self.assertIsNone(m.RELEASE)

    def test_unreleased_template_never_enters_transaction(self):
        m = self.m
        draft = m.prepare_release({}, 'a' * 40, 'b' * 40)
        self.assertEqual(draft['status'], 'NOT_RELEASED')
        with self.assertRaisesRegex(m.Refusal, 'cleanup-not-released'): m.configure(draft, True)


if __name__ == '__main__':
    unittest.main()
