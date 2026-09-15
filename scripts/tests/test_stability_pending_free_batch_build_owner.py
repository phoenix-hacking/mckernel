"""Cheap contract tests for the pending-free candidate12 build owner.

These tests deliberately do not invoke Docker, compilers, a guest, or the
production lock.  They exercise only static profile/result rejection paths.
"""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
OWNER = ROOT / 'docs/verification/evidence/stability-pending-free-batch-build-owner-20260915.py'
spec = importlib.util.spec_from_file_location('pending_free_build_owner', OWNER)
owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)


def inspect_row(config):
    """The accepted owner profile, with the new fixed harness argv only."""
    nonce, cid = config['nonce'], config['container_id']
    return {'Id': cid, 'Name': '/' + config['name'], 'Image': owner.IMAGE_ID,
            'Path': owner.PYTHON, 'Args': owner.harness_argv(),
            'Config': {'Hostname': cid[:12], 'Labels': {'mckernel.collector.owner': nonce},
                       'User': '1000:1000', 'Image': owner.IMAGE_ID, 'WorkingDir': '/work',
                       'Entrypoint': [owner.PYTHON], 'Cmd': owner.harness_argv(), 'Tty': False,
                       'OpenStdin': False, 'StdinOnce': False, 'AttachStdin': False, 'Domainname': '',
                       'Env': ['TMPDIR=/work/tmp', 'HOME=/tmp', 'PYTHONDONTWRITEBYTECODE=1']},
            'HostConfig': {'NetworkMode': 'none', 'Privileged': False, 'ReadonlyRootfs': True,
                           'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'], 'GroupAdd': [],
                           'Memory': 12884901888, 'MemorySwap': 12884901888, 'NanoCpus': 4000000000,
                           'CpusetCpus': '2-5', 'PidsLimit': 512, 'CgroupParent': '/mckernel-dev',
                           'Init': True, 'PidMode': '', 'UTSMode': '', 'UsernsMode': '', 'IpcMode': 'private',
                           'Runtime': 'runc', 'AutoRemove': False, 'PublishAllPorts': False,
                           'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}, 'CgroupnsMode': '',
                           'ShmSize': 67108864, 'OomKillDisable': False, 'MemorySwappiness': -1,
                           'OomScoreAdj': 0, 'LogConfig': {'Type': 'json-file', 'Config': {}},
                           'Ulimits': [{'Hard': 0, 'Name': 'core', 'Soft': 0},
                                       {'Hard': 4096, 'Name': 'nofile', 'Soft': 4096}],
                           'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
                           'MaskedPaths': ['/proc/kcore', '/proc/keys', '/proc/latency_stats', '/proc/timer_list', '/proc/scsi', '/sys/firmware'],
                           'ReadonlyPaths': ['/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger'],
                           'Mounts': [{'Type': 'bind', 'Source': str(owner.REPO), 'Target': '/workspace', 'ReadOnly': True},
                                      {'Type': 'bind', 'Source': config['mount'], 'Target': '/work', 'ReadOnly': False}]},
            'Mounts': [{'Type': 'bind', 'Source': str(owner.REPO), 'Destination': '/workspace', 'RW': False, 'Propagation': 'rprivate'},
                       {'Type': 'bind', 'Source': config['mount'], 'Destination': '/work', 'RW': True, 'Propagation': 'rprivate'}],
            'NetworkSettings': {'Networks': {'none': {'IPAddress': '', 'GlobalIPv6Address': '',
                                                        'Gateway': '', 'IPv6Gateway': '', 'MacAddress': ''}}}}


class PendingFreeOwnerTests(unittest.TestCase):
    def test_exact_isolated_uid1000_entrypoint(self):
        argv = owner.expected_create('a' * 32, Path('/scratch/fresh'))
        for flag in ('--cpus=4', '--cpuset-cpus=2-5', '--memory=12g', '--memory-swap=12g',
                     '--pids-limit=512', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                     '--read-only', '--network=none', '--user=1000:1000'):
            self.assertIn(flag, argv)
        self.assertNotIn('rustup', ' '.join(argv)); self.assertNotIn('+nightly', argv)
        self.assertEqual(argv[-8:], ['-B', owner.HARNESS, '--output-dir', owner.CONTAINER_OUTPUT,
                                     '--rustc', owner.RUSTC, '--cc', owner.GCC])

    def test_profile_rejects_entrypoint_and_capability_drift(self):
        config = {'nonce': 'b' * 32, 'name': 'mckernel-collector-' + 'b' * 32,
                  'container_id': 'c' * 64, 'mount': '/scratch/fresh'}
        image = {'Id': owner.IMAGE_ID, 'Architecture': 'amd64', 'Os': 'linux',
                 'Config': {'Env': []}, 'RootFS': {'Type': 'layers', 'Layers': []}}
        row = inspect_row(config)
        owner.full_inspect(row, config, image, copy.deepcopy(image))
        mutations = (
            lambda r: r.__setitem__('Args', ['-c', 'id']),
            lambda r: r['Config'].__setitem__('Cmd', ['-B', owner.HARNESS, '--rustc', '/tmp/rustc']),
            lambda r: r['HostConfig'].__setitem__('Privileged', True),
            lambda r: r['HostConfig'].__setitem__('Devices', ['/dev/kvm']),
            lambda r: r['Mounts'].__setitem__(0, {**r['Mounts'][0], 'RW': True}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                drift = copy.deepcopy(row); mutate(drift)
                with self.assertRaises(ValueError): owner.full_inspect(drift, config, image, copy.deepcopy(image))

    def test_source_and_six_input_pins_are_exact(self):
        self.assertEqual(len(owner.pinned_inputs()), 6)
        for path, expected in owner.pinned_inputs().items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        source = OWNER.read_text()
        for required in ('compiler_copies', 'RUSTC_SHA', 'GCC_SHA', 'recover_cleanup',
                         'watchdog-config.json', 'original-tree-inventory.json',
                         "'--rustc', RUSTC", "'--cc', GCC"):
            self.assertIn(required, source)

    def result_fixture(self, td):
        """Synthetic complete evidence; this test never claims fixture execution."""
        mount, host = Path(td) / 'mount', Path(td) / 'host'
        out = mount / owner.OUTPUT_NAME
        out.mkdir(parents=True); host.mkdir()
        (out / 'inputs').mkdir(); (out / 'explicit-output-control').mkdir()
        for name in owner.artifact_names():
            (out / name).write_bytes(b'synthetic binary or stream\n')
        for path in owner.PINNED_INPUTS:
            (out / 'inputs' / Path(path).name).write_bytes((ROOT / path).read_bytes())
        contract = owner.harness_contract()
        prelude, bindings = contract['prelude']()
        fixture = (ROOT / 'kernel/rust/tests/pending_free_batch_vectors.rs').read_text()
        (out / 'actual_extracted_and_vectors.rs').write_text(prelude + '\n// fixture appended verbatim\n' + fixture)
        needle = 'let rc=drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None});'
        replacement = 'let rc=if name=="later-invalid" {mem_finish_free_pages_pending_result(&raw mut self.b.as_mut().get_unchecked_mut().head,Some(free_page))}else{drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None})};'
        (out / 'partial-release-mutant.rs').write_text(prelude + '\n' + fixture.replace(needle, replacement))
        def link(n=0): return {'next': n, 'prev': n}
        snapshot = {'source': link(), 'other': link(), 'batch': {'head': link(3), 'state': 1, 'source': 1},
                    'pages': [{'list': link(), 'hash': link(20+i), 'mode': 1, 'phys': 100+i, 'count': 70+i, 'mapped': 80+i, 'offset': i+1, 'pgshift': 12+i} for i in range(4)]}
        rows = []
        for case, op, rc in contract['EXPECTED']:
            before = copy.deepcopy(snapshot)
            if case == 'later-invalid': before['pages'][1]['mode'] = 0
            callbacks = [[100+i, i+1, 1] for i in range(rc)] if op in ('drain', 'finish') and rc > 0 else []
            if case == 'source-reuse' and op == 'finish': callbacks = [[102, 7, 1]]
            if case == 'other-head-finish': callbacks = [[103, 4, 1]]
            rows.append({'case': case, 'op': op, 'rc': rc, 'before': before, 'after': copy.deepcopy(before), 'callbacks': callbacks})
        bad = copy.deepcopy(rows[7]); bad['callbacks'] = [[100, 1, 1]]
        bad['after']['pages'][0]['mode'] = 0; bad['after']['pages'][0]['list'] = {'next': 90, 'prev': 91}
        def stream(rows): return ''.join('JSON|' + json.dumps(row) + '\n' for row in rows)
        (out / 'rust-run.stdout').write_text(stream(rows) + 'CONTROL|callback-borrow-and-capacity-observed\n')
        (out / 'c-run.stdout').write_text(stream(rows))
        (out / 'mutant-run.stdout').write_text(stream(rows[:7] + [bad]))
        (out / 'mutant-run.stderr').write_text('PARTIAL_RELEASE_DETECTED case=later-invalid\n')
        (out / 'rustc-identity.stdout').write_text(owner.RUSTC_RELEASE + '\n' + owner.RUSTC_COMMIT + '\n')
        (out / 'cc-identity.stdout').write_text('gcc reviewed immutable image\n')
        traits = {}
        for trait in owner.TRAITS:
            (out / (trait + '.rs')).write_text(prelude + '\nfn need<T:' + trait + '>(){} fn main(){need::<PendingFreeBatch>();}\n')
            (out / ('trait-' + trait + '.stdout')).write_bytes(b'')
            diagnostic = {'level': 'error', 'code': {'code': 'E0277'}, 'rendered': 'PendingFreeBatch does not implement ' + trait}
            (out / ('trait-' + trait + '.stderr')).write_text(json.dumps(diagnostic) + '\n')
            traits[trait] = {'status': 'EXPECTED_E0277_ONLY', 'diagnostic_count': 1}
        env = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C', 'LC_ALL': 'C'}
        commands = []
        for i, (label, argv) in enumerate(owner.command_contract()):
            row = {'label': label, 'argv': argv, 'cwd': '/workspace', 'environment': env,
                   'timeout_seconds': 120, 'started_ns': 100+i*2, 'finished_ns': 101+i*2,
                   'returncode': 101 if label == 'mutant-run' else 1 if label.startswith('trait-') else 0}
            for name in ('stdout', 'stderr'): row[name + '_sha256'] = owner.digest(out / (label + '.' + name))
            commands.append(row)
        manifest = {'status': 'PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY', 'scope': 'source fixture only; no runtime or production credit',
                    'inputs': owner.pinned_inputs(), 'commands': commands, 'expected': [list(r) for r in contract['EXPECTED']],
                    'rust_rows': rows, 'c_rows': copy.deepcopy(rows), 'mutant_detected': bad, 'trait_negatives': traits}
        def js(name, value): (out / name).write_text(json.dumps(value))
        js('manifest.json', manifest); js('commands.json', commands)
        js('input-manifest.json', {'inputs': owner.pinned_inputs(), 'environment': env, 'platform': 'synthetic', 'harness_argv': owner.harness_argv()[1:], 'cwd': '/work'})
        js('source-extraction.json', {'inputs': owner.pinned_inputs(), 'items': bindings})
        js('output-modes.json', {'status': 'PASS', 'default': '/work/tmp/mckernel-pending-candidate10_ignored'.replace('10_', '10-'), 'explicit': owner.CONTAINER_OUTPUT + '/explicit-output-control'})
        self.rehash(out)
        return mount, host, out, manifest

    def rehash(self, out):
        (out / 'artifact-manifest.json').write_text(json.dumps({name: owner.digest(out / name) for name in owner.artifact_names() if (out / name).exists()}))

    def test_complete_result_accepts_only_expected_negative_controls(self):
        with tempfile.TemporaryDirectory() as td:
            mount, host, out, expected = self.result_fixture(td)
            actual, identity = owner.verify_result(mount, host, owner.pinned_inputs())
            self.assertEqual(actual, expected); self.assertEqual(identity['sha256'], owner.digest(out / 'manifest.json'))

    def test_manifest_and_command_mutations(self):
        changes = [
            lambda m: m['expected'].pop(), lambda m: m['rust_rows'].pop(),
            lambda m: m['c_rows'][0].__setitem__('rc', 1),
            lambda m: m['rust_rows'][0]['before'].__setitem__('pages', []),
            lambda m: m['mutant_detected'].__setitem__('callbacks', []),
            lambda m: m['trait_negatives'].pop('Sync'),
        ]
        for index in range(15):
            changes.extend([lambda m, i=index: m['commands'][i].__setitem__('argv', ['wrong']),
                            lambda m, i=index: m['commands'][i].__setitem__('returncode', 0 if i in range(8, 14) else 1)])
        changes.extend([lambda m: m['commands'][0].__setitem__('timeout_seconds', True),
                        lambda m: m['commands'][0].__setitem__('finished_ns', 120000000101),
                        lambda m: m['commands'][0].__setitem__('started_ns', -1),
                        lambda m: m['commands'][0].__setitem__('cwd', '/tmp'),
                        lambda m: m['commands'][0]['environment'].__setitem__('RUSTUP_HOME', '/bad'),
                        lambda m: m['commands'][0].__setitem__('stdout_sha256', '0'*64)])
        for i, mutate in enumerate(changes):
            with self.subTest(mutation=i), tempfile.TemporaryDirectory() as td:
                mount, host, out, manifest = self.result_fixture(td)
                mutate(manifest)
                (out / 'manifest.json').write_text(json.dumps(manifest))
                (out / 'commands.json').write_text(json.dumps(manifest['commands']))
                self.rehash(out)
                with self.assertRaises(ValueError): owner.verify_result(mount, host, owner.pinned_inputs())

    def test_every_required_artifact_omission(self):
        for name in sorted(owner.artifact_names()):
            with self.subTest(artifact=name), tempfile.TemporaryDirectory() as td:
                mount, host, out, _ = self.result_fixture(td)
                (out / name).unlink(); self.rehash(out)
                with self.assertRaises(ValueError): owner.verify_result(mount, host, owner.pinned_inputs())

    def test_ledger_stream_and_diagnostic_mismatch(self):
        changes = [('commands.json', b'[]'), ('rust-run.stdout', b''), ('c-run.stdout', b''),
                   ('mutant-run.stderr', b'unrelated failure'), ('partial-release-mutant.rs', b'wrong source')]
        for trait in owner.TRAITS:
            changes.extend([('trait-' + trait + '.stdout', b'unexpected'),
                            ('trait-' + trait + '.stderr', b'{"level":"error","code":{"code":"E0001"},"rendered":"PendingFreeBatch ' + trait.encode() + b'"}\n')])
        for name, data in changes:
            with self.subTest(artifact=name), tempfile.TemporaryDirectory() as td:
                mount, host, out, manifest = self.result_fixture(td)
                (out / name).write_bytes(data)
                # Rebind stream hashes to exercise semantic diagnostics too.
                for row in manifest['commands']:
                    for suffix in ('stdout', 'stderr'):
                        row[suffix + '_sha256'] = owner.digest(out / (row['label'] + '.' + suffix))
                (out / 'manifest.json').write_text(json.dumps(manifest))
                if name != 'commands.json': (out / 'commands.json').write_text(json.dumps(manifest['commands']))
                self.rehash(out)
                with self.assertRaises(ValueError): owner.verify_result(mount, host, owner.pinned_inputs())

    def test_noncanonical_artifacts_and_symlinks(self):
        for name in ('../outside', '/tmp/absolute', './manifest.json', 'inputs//abi.rs', 'inputs/../manifest.json'):
            with self.subTest(path=name), tempfile.TemporaryDirectory() as td:
                mount, host, out, _ = self.result_fixture(td)
                artifacts = json.loads((out / 'artifact-manifest.json').read_text()); artifacts[name] = '0'*64
                (out / 'artifact-manifest.json').write_text(json.dumps(artifacts))
                with self.assertRaises(ValueError): owner.verify_result(mount, host, owner.pinned_inputs())
        for name in ('manifest.json', 'inputs', 'explicit-output-control'):
            with self.subTest(symlink=name), tempfile.TemporaryDirectory() as td:
                mount, host, out, _ = self.result_fixture(td)
                target = out / name; renamed = Path(td) / ('saved-' + name)
                target.rename(renamed); target.symlink_to(renamed)
                with self.assertRaises((ValueError, OSError)): owner.verify_result(mount, host, owner.pinned_inputs())


if __name__ == '__main__':
    unittest.main(verbosity=2)
