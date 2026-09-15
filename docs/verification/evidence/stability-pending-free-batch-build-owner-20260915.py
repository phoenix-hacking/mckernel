#!/usr/bin/env python3
"""Bounded UID1000 owner for pending-free candidate12 only.

This is infrastructure evidence.  It uses the accepted collector owner's
lock/watchdog/recovery implementation without borrowing its build inventory.
No application, transport, guest, or production acceptance is implied.
"""
import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import traceback

REPO = Path('/home/holden/mckernel')
WORK = Path('/home/holden/mckernel-work')
DOCKER = '/usr/bin/docker'
PYTHON = '/usr/bin/python3'
LOCK = Path('/run/lock/mckernel-development.lock')
IMAGE_ID = 'sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94'
IMAGE_MANIFEST_SHA = 'c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a'
RUSTC = '/usr/bin/rustc'
RUSTC_RELEASE = 'release: 1.92.0'
RUSTC_COMMIT = 'commit-hash: ded5c06cf21d2b93bffd5d884aa6e96934ee4234'
RUSTC_SHA = '38eeb1652fb59753cb7736e354ec1579a543da9a2eb8a68be102a41e88eb5dc6'
GCC = '/usr/bin/gcc'
GCC_SHA = '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'
OUTPUT_NAME = 'pending-free-batch-candidate12'
CONTAINER_OUTPUT = '/work/' + OUTPUT_NAME
HARNESS = '/workspace/kernel/rust/tests/pending_free_batch_actual_harness.py'
BASE_PATH = REPO / 'docs/verification/evidence/stability-linux-collector-build-owner-20260915.py'
BASE_SHA = 'ba1ed0320e36e24cf59c394b7466a25e6906be179f19924f221d54c759bf7979'

PINNED_INPUTS = {
    'kernel/rust/abi.rs': 'ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e',
    'kernel/rust/mem_helpers.rs': '3bdb98c725f56795d8aa05273db9bd68a15aae3efb5b205836c6c995f73b02ca',
    'kernel/rust/tests/pending_free_batch_vectors.rs': 'ee38d7d27a2c68e04fc3ac8433faf8d923e33580a6c55968bac927f6e01a33bb',
    'kernel/rust/tests/pending_free_batch_vectors.c': '0eb14ca2ee9b7e085d21be76cab087b673532d3abd2f86bbeb5b199f09f29890',
    'kernel/rust/tests/run_equivalence.sh': '14cbdf9421c5d284ded0a607324c60a72f5d628fe55e99139d135986e9cbb145',
    'kernel/rust/tests/pending_free_batch_actual_harness.py': '298af617437bd5beef1643286532c3cff7e14c30f0be263d414f93de47dc3cfc',
}


def _load_base():
    require_hash = hashlib.sha256(BASE_PATH.read_bytes()).hexdigest()
    if require_hash != BASE_SHA:
        raise ValueError('accepted owner source drift')
    spec = importlib.util.spec_from_file_location('pending_free_base_owner', BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()
require = base.require
digest = base.digest
regular = base.regular
write = base.write
save = base.save
strict_json = base.strict_json
same = base.same
stat_identity = base.stat_identity
CID = base.CID
CGROUP = base.CGROUP
MAX_FILE = base.MAX_FILE
reviewed_owner = base.reviewed_owner


def pinned_inputs():
    return dict(PINNED_INPUTS)


def harness_argv():
    return ['-B', HARNESS, '--output-dir', CONTAINER_OUTPUT, '--rustc', RUSTC, '--cc', GCC]


def expected_create(nonce, mount):
    name = 'mckernel-collector-' + nonce
    return [DOCKER, 'create', '--pull=never', '--init', '--name', name, '--label',
            'mckernel.collector.owner=' + nonce, '--cpus=4', '--cpuset-cpus=2-5',
            '--cgroup-parent=/mckernel-dev', '--memory=12g', '--memory-swap=12g',
            '--pids-limit=512', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--read-only', '--network=none', '--user=1000:1000', '--ulimit', 'core=0',
            '--ulimit', 'nofile=4096:4096', '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m',
            '--mount', 'type=bind,src=' + str(REPO) + ',dst=/workspace,readonly',
            '--mount', 'type=bind,src=' + str(mount) + ',dst=/work', '--env', 'TMPDIR=/work/tmp',
            '--env', 'HOME=/tmp', '--env', 'PYTHONDONTWRITEBYTECODE=1', '--workdir=/work',
            '--entrypoint=' + PYTHON, IMAGE_ID] + harness_argv()


def owned(row, config):
    require(type(row.get('Id')) is str and CID.fullmatch(row['Id']), 'full container ID')
    require(row['Id'] == config['container_id'] and row.get('Name') == '/' + config['name'], 'owned container identity')
    require(row.get('Image') == IMAGE_ID and row.get('Config', {}).get('Labels', {}).get('mckernel.collector.owner') == config['nonce'], 'owned image/label')


def full_inspect(row, config, image, retained_image):
    """Retain the accepted exhaustive profile checker with a fixed new argv."""
    owned(row, config)
    require(row.get('Path') == PYTHON and row.get('Args') == harness_argv(), 'exact candidate11 entrypoint')
    require(row.get('Config', {}).get('Entrypoint') == [PYTHON] and row.get('Config', {}).get('Cmd') == harness_argv(), 'exact candidate11 Config argv')
    translated = copy.deepcopy(row)
    legacy = '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'
    translated['Path'] = PYTHON; translated['Args'] = ['-B', legacy]
    translated['Config']['Entrypoint'] = [PYTHON]; translated['Config']['Cmd'] = ['-B', legacy]
    base.full_build_inspect(translated, config, image, retained_image)


class Commands(base.Commands):
    def __init__(self, host, supervisor, deadline=None):
        super().__init__(host, supervisor, deadline)


def lookup(commands, config, label):
    filters = ['label=mckernel.collector.owner=' + config['nonce'], 'name=^/' + config['name'] + '$', 'id=' + config['container_id']]
    rows = []
    for number, value in enumerate(filters):
        raw, _ = commands.run('%s-lookup-%d' % (label, number), [DOCKER, 'container', 'ls', '--all', '--no-trunc', '--filter', value, '--format', '{{.ID}}'])
        found = raw.decode('ascii').splitlines(); require(len(found) <= 1 and all(CID.fullmatch(item) for item in found), 'bounded owned lookup')
        rows.append(found)
    require(all(value == rows[0] for value in rows), 'lookup ambiguity')
    if not rows[0]: return None
    raw, _ = commands.run(label + '-inspect', [DOCKER, 'inspect', rows[0][0]])
    row = base.one_inspect(raw); owned(row, config); return row


def compiler_copies(commands, config, host):
    copied = []
    for label, path, expected in (('rustc', RUSTC, RUSTC_SHA), ('gcc', GCC, GCC_SHA)):
        destination = host / ('image-' + label)
        commands.run('preverify-copy-' + label, [DOCKER, 'cp', config['container_id'] + ':' + path, str(destination)], 120)
        raw, identity = regular(destination, 256 * 1024 * 1024)
        require(identity['sha256'] == expected and len(raw) == identity['size'], 'immutable image compiler hash: ' + label)
        copied.append({'path': path, 'host_copy': str(destination), 'sha256': identity['sha256'], 'size': identity['size']})
    save(host / 'compiler-preverification.json', {'image': IMAGE_ID, 'compilers': copied, 'pre_start': True, 'application_acceptance': False})
    return copied


def _artifact(path):
    raw, identity = regular(path)
    return raw, {'path': str(path), 'size': len(raw), 'sha256': identity['sha256']}


TRAITS = ('Copy', 'Clone', 'Unpin', 'Send', 'Sync')


def harness_contract():
    path = REPO / 'kernel/rust/tests/pending_free_batch_actual_harness.py'
    raw, identity = regular(path)
    require(identity['sha256'] == PINNED_INPUTS[str(path.relative_to(REPO))], 'reviewed harness drift')
    namespace = {'__file__': str(path), '__name__': 'reviewed_pending_free_contract'}
    exec(compile(raw, str(path), 'exec'), namespace)
    return namespace


def command_contract():
    out = CONTAINER_OUTPUT
    rust = [RUSTC, '--edition=2021', '-D', 'warnings']
    rows = [
        ('bash-syntax', ['bash', '-n', '/workspace/kernel/rust/tests/run_equivalence.sh']),
        ('rustc-identity', [RUSTC, '--version', '--verbose']),
        ('cc-identity', [GCC, '--version']),
        ('rust-compile', rust + [out + '/actual_extracted_and_vectors.rs', '-o', out + '/actual']),
        ('rust-run', [out + '/actual']),
        ('c-compile', [GCC, '-std=c11', '-Wall', '-Wextra', '-Werror', '/workspace/kernel/rust/tests/pending_free_batch_vectors.c', '-o', out + '/reference-c']),
        ('c-run', [out + '/reference-c']),
        ('mutant-compile', rust + [out + '/partial-release-mutant.rs', '-o', out + '/partial-release-mutant']),
        ('mutant-run', [out + '/partial-release-mutant']),
    ]
    rows += [('trait-' + trait, rust + ['--error-format=json', out + '/' + trait + '.rs', '-o', out + '/' + trait]) for trait in TRAITS]
    return rows + [('diff-check', ['git', 'diff', '--check'])]


def artifact_names():
    names = {'manifest.json', 'commands.json', 'input-manifest.json', 'output-modes.json',
             'source-extraction.json', 'actual_extracted_and_vectors.rs', 'actual', 'reference-c',
             'partial-release-mutant.rs', 'partial-release-mutant'}
    names.update('inputs/' + Path(path).name for path in PINNED_INPUTS)
    names.update(trait + '.rs' for trait in TRAITS)
    names.update(label + suffix for label, _ in command_contract() for suffix in ('.stdout', '.stderr'))
    return names


def validate_rows(rows, contract):
    require(type(rows) is list and len(rows) == 30, 'all thirty computed rows')
    for row in rows:
        require(type(row) is dict and set(row) == {'case', 'op', 'rc', 'before', 'after', 'callbacks'}, 'computed row fields')
        require(type(row['rc']) is int and type(row['callbacks']) is list, 'computed result types')
        for snapshot in (row['before'], row['after']):
            require(type(snapshot) is dict and set(snapshot) == {'source', 'other', 'batch', 'pages'}, 'snapshot fields')
            batch = snapshot['batch']
            require(type(batch) is dict and set(batch) == {'head', 'state', 'source'} and type(batch['state']) is int and batch['state'] in (0, 1, 2) and type(batch['source']) is int, 'batch fields')
            pages = snapshot['pages']
            require(type(pages) is list and len(pages) == 4, 'four complete page snapshots')
            links = [snapshot['source'], snapshot['other'], batch['head']]
            for i, page in enumerate(pages):
                require(type(page) is dict and set(page) == {'list', 'hash', 'mode', 'phys', 'count', 'mapped', 'offset', 'pgshift'}, 'page fields')
                require(all(type(page[k]) is int for k in ('mode', 'phys', 'count', 'mapped', 'offset', 'pgshift')), 'page scalar types')
                require((page['phys'], page['count'], page['mapped'], page['pgshift']) == (100+i, 70+i, 80+i, 12+i), 'computed page identity')
                links.extend([page['list'], page['hash']])
            for link in links:
                require(type(link) is dict and set(link) == {'next', 'prev'} and all(type(n) is int and n in (0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 90, 91) for n in link.values()), 'computed link identity')
    try:
        contract['check_rows'](rows)
    except (AssertionError, KeyError, TypeError, StopIteration, IndexError) as error:
        raise ValueError('computed case oracle: ' + str(error)) from error


def verify_result(mount, host, input_hashes):
    require(input_hashes == PINNED_INPUTS, 'exact owner input pins')
    output = Path(mount) / OUTPUT_NAME
    directory_fd = base.directory(output)
    os.close(directory_fd)
    artifacts = strict_json(regular(output / 'artifact-manifest.json')[0])
    require(type(artifacts) is dict, 'artifact map')
    for name, sha in artifacts.items():
        require(type(name) is str and name and not name.startswith('/') and all(part not in ('', '.', '..') for part in name.split('/')) and str(Path(name)) == name, 'canonical relative artifact name')
        require(type(sha) is str and re.fullmatch('[0-9a-f]{64}', sha), 'artifact hash encoding')
    require(set(artifacts) == artifact_names(), 'complete fixed artifact membership')
    # Enumerate only these two fixed directories. No glob follows an untrusted
    # directory; every read below walks parents with O_NOFOLLOW and is bounded.
    require(set(os.listdir(output)) == {n for n in artifacts if '/' not in n} | {'artifact-manifest.json', 'inputs', 'explicit-output-control'}, 'exact output directory membership')
    for name in ('inputs', 'explicit-output-control'):
        fd = base.directory(output / name)
        try:
            entries = set(os.listdir(fd))
        finally:
            os.close(fd)
        wanted = {Path(n).name for n in artifacts if n.startswith('inputs/')} if name == 'inputs' else set()
        require(entries == wanted, 'exact child directory membership: ' + name)
    contents = {}
    for name, sha in artifacts.items():
        raw, identity = regular(output / name)
        require(identity['sha256'] == sha, 'result artifact digest: ' + name)
        contents[name] = raw
    manifest = strict_json(contents['manifest.json'])
    require(set(manifest) == {'status', 'scope', 'inputs', 'commands', 'expected', 'rust_rows', 'c_rows', 'mutant_detected', 'trait_negatives'}, 'exact harness result inventory')
    require(manifest['status'] == 'PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY' and manifest['scope'] == 'source fixture only; no runtime or production credit', 'focused-only result')
    contract = harness_contract()
    require(manifest['inputs'] == input_hashes and manifest['expected'] == [list(r) for r in contract['EXPECTED']], 'exact expected cases and inputs')
    require(manifest['rust_rows'] == manifest['c_rows'], 'complete Rust/C equality')
    validate_rows(manifest['rust_rows'], contract)
    frozen = strict_json(contents['input-manifest.json'])
    require(set(frozen) == {'inputs', 'environment', 'platform', 'harness_argv', 'cwd'} and frozen['inputs'] == input_hashes and frozen['cwd'] == '/work' and frozen['harness_argv'] == harness_argv()[1:] and type(frozen['platform']) is str and frozen['platform'], 'frozen harness invocation')
    env = frozen['environment']
    require(type(env) is dict and set(env) <= {'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL'} and env.get('LANG') == env.get('LC_ALL') == 'C' and env.get('HOME') == '/tmp' and type(env.get('PATH')) is str and env['PATH'] and all(type(v) is str for v in env.values()), 'bounded explicit harness environment')
    for relative, expected in input_hashes.items():
        require(artifacts['inputs/' + Path(relative).name] == expected, 'frozen source binding: ' + relative)
    commands = manifest['commands']
    require(type(commands) is list and commands == strict_json(contents['commands.json']) and len(commands) == len(command_contract()), 'independent command ledger agreement')
    previous = 0
    for row, (label, argv) in zip(commands, command_contract()):
        require(type(row) is dict and set(row) == {'label', 'argv', 'cwd', 'environment', 'timeout_seconds', 'started_ns', 'finished_ns', 'returncode', 'stdout_sha256', 'stderr_sha256'}, 'complete exact command fields')
        require(row['label'] == label and row['argv'] == argv and row['cwd'] == '/workspace' and row['environment'] == env, 'exact command invocation: ' + label)
        require(type(row['timeout_seconds']) is int and row['timeout_seconds'] == 120 and type(row['started_ns']) is int and type(row['finished_ns']) is int and previous <= row['started_ns'] <= row['finished_ns'] <= row['started_ns'] + 120000000000, 'bounded ordered command times: ' + label)
        previous = row['finished_ns']
        require(type(row['returncode']) is int and (1 <= row['returncode'] <= 255 if label == 'mutant-run' or label.startswith('trait-') else row['returncode'] == 0), 'exact command outcome: ' + label)
        for stream in ('stdout', 'stderr'):
            require(row[stream + '_sha256'] == artifacts[label + '.' + stream], 'command stream digest: ' + label)
    require(RUSTC_RELEASE in contents['rustc-identity.stdout'].decode() and RUSTC_COMMIT in contents['rustc-identity.stdout'].decode() and contents['cc-identity.stdout'], 'retained compiler versions')
    for label, key in (('rust-run', 'rust_rows'), ('c-run', 'c_rows')):
        require(contract['rows'](contents[label + '.stdout'].decode()) == manifest[key], 'computed stdout rows: ' + label)
    require(b'CONTROL|callback-borrow-and-capacity-observed' in contents['rust-run.stdout'], 'callback control')
    mutant = contract['rows'](contents['mutant-run.stdout'].decode())
    require(len(mutant) == 8 and mutant[:-1] == manifest['rust_rows'][:7], 'mutant target and exact retained prefix')
    bad = mutant[-1]
    require(bad == manifest['mutant_detected'] and bad['case'] == 'later-invalid' and bad['op'] == 'drain' and type(bad['rc']) is int and bad['rc'] == -22 and bad['callbacks'] == [[100, 1, 1]], 'retained partial-release mutation')
    require(bad['before'] == manifest['rust_rows'][7]['before'] and bad['before']['pages'][0]['mode'] == 1 and bad['after']['pages'][0]['mode'] == 0 and bad['after']['pages'][0]['list'] == {'next': 90, 'prev': 91} and bad['before']['pages'][1]['mode'] == bad['after']['pages'][1]['mode'] == 0 and b'PARTIAL_RELEASE_DETECTED case=later-invalid' in contents['mutant-run.stderr'], 'actual mutant partial release')
    require(type(manifest['trait_negatives']) is dict and set(manifest['trait_negatives']) == set(TRAITS), 'all five trait negatives')
    for trait in TRAITS:
        require(contents['trait-' + trait + '.stdout'] == b'', 'empty negative stdout')
        diagnostics = [strict_json(line) for line in contents['trait-' + trait + '.stderr'].splitlines()]
        coded = [d for d in diagnostics if d.get('code')]
        require(coded and all(d.get('level') == 'error' and d['code'].get('code') == 'E0277' and trait in d.get('rendered', '') and 'PendingFreeBatch' in d.get('rendered', '') for d in coded), 'expected E0277 diagnostic: ' + trait)
        require(all(d.get('level') != 'warning' and (d.get('code') or d.get('message', '').startswith(('aborting due to', 'For more information'))) for d in diagnostics), 'only expected negative diagnostics')
        require(manifest['trait_negatives'][trait] == {'status': 'EXPECTED_E0277_ONLY', 'diagnostic_count': len(coded)}, 'negative summary binding')
    modes = strict_json(contents['output-modes.json'])
    require(set(modes) == {'default', 'explicit', 'status'} and modes['status'] == 'PASS' and modes['explicit'] == CONTAINER_OUTPUT + '/explicit-output-control' and type(modes['default']) is str and re.fullmatch('/work/tmp/mckernel-pending-candidate10-[a-z0-9_]+', modes['default']), 'output mode controls')
    prelude, bindings = contract['prelude']()
    fixture = contents['inputs/pending_free_batch_vectors.rs'].decode()
    require(strict_json(contents['source-extraction.json']) == {'items': bindings, 'inputs': input_hashes}, 'exact source extraction bindings')
    require(contents['actual_extracted_and_vectors.rs'] == (prelude + '\n// fixture appended verbatim\n' + fixture).encode(), 'exact extracted production and fixture source')
    needle = 'let rc=drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None});'
    replacement = 'let rc=if name=="later-invalid" {mem_finish_free_pages_pending_result(&raw mut self.b.as_mut().get_unchecked_mut().head,Some(free_page))}else{drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None})};'
    require(fixture.count(needle) == 1 and contents['partial-release-mutant.rs'] == (prelude + '\n' + fixture.replace(needle, replacement)).encode(), 'exact partial-release mutant source')
    for trait in TRAITS:
        require(contents[trait + '.rs'] == (prelude + '\nfn need<T:' + trait + '>(){} fn main(){need::<PendingFreeBatch>();}\n').encode(), 'exact trait probe source')
    manifest_id = {'path': str(output / 'manifest.json'), 'size': len(contents['manifest.json']), 'sha256': artifacts['manifest.json']}
    write(Path(host) / 'harness-manifest.json', contents['manifest.json'])
    save(Path(host) / 'harness-bindings.json', {'manifest': manifest_id, 'six_inputs': input_hashes, 'compiler_hashes': {'rustc': RUSTC_SHA, 'gcc': GCC_SHA}, 'application_acceptance': False, 'production_gate_credit': False})
    return manifest, manifest_id


def first_failure(host, phase, error):
    try: save(Path(host) / 'first-failure.json', {'phase': phase, 'type': type(error).__name__, 'message': str(error), 'monotonic': time.monotonic(), 'application_acceptance': False, 'transport_acceptance': False})
    except FileExistsError: pass


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt-number', type=int, required=True); parser.add_argument('--owner-sha256', required=True); args = parser.parse_args()
    require(os.getuid() == os.geteuid() == 0 and 1 <= args.attempt_number <= 999999, 'root bounded attempt')
    require(digest(Path(__file__).resolve()) == args.owner_sha256, 'owner source identity')
    input_hashes = pinned_inputs()
    require(all(digest(REPO / path) == sha for path, sha in input_hashes.items()), 'six pinned input identities')
    suffix = '20260915-%d' % args.attempt_number; host = WORK / ('scratch/stability-pending-free-build-owner-' + suffix); mount = WORK / ('scratch/stability-pending-free-build-mount-' + suffix)
    require(not host.exists() and not host.is_symlink() and not mount.exists() and not mount.is_symlink(), 'fresh paths')
    os.umask(0o077); host.mkdir(mode=0o700); (host / 'docker-home').mkdir(mode=0o700); (host / 'docker-config').mkdir(mode=0o700); mount.mkdir(mode=0o700); os.chown(mount, 1000, 1000); os.chmod(mount, 0o700)
    (mount / 'tmp').mkdir(mode=0o700); os.chown(mount / 'tmp', 1000, 1000)
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600); require(stat.S_ISREG(os.fstat(lock_fd).st_mode) and os.fstat(lock_fd).st_uid == 0 and os.fstat(lock_fd).st_nlink == 1, 'root regular lock'); fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    nonce = os.urandom(16).hex(); config = {'host': str(host), 'mount': str(mount), 'nonce': nonce, 'name': 'mckernel-collector-' + nonce, 'image': IMAGE_ID, 'container_id': None, 'application_acceptance': False, 'transport_acceptance': False}
    result = {'status': 'FAIL', 'application_acceptance': False, 'transport_acceptance': False, 'backend_enabled': False, 'diagnostic_errors': [], 'watchdog_raw_wait_status': None}
    commands = watch = control = supervisor = None
    try:
        supervisor_raw, supervisor_id = regular(base.FIXTURES / 'supervisor_host38.py'); require(supervisor_id['sha256'] == base.SUPERVISOR_SHA, 'reviewed supervisor drift'); write(host / 'supervisor.py', supervisor_raw)
        orchestrator_raw, orchestrator_id = regular(base.FIXTURES / 'root_orchestrator.py'); require(orchestrator_id['sha256'] == base.ORCHESTRATOR_SHA, 'reviewed watchdog drift'); write(host / 'root_orchestrator.py', orchestrator_raw)
        spec = importlib.util.spec_from_file_location('pending_free_supervisor', host / 'supervisor.py'); supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor); commands = Commands(host, supervisor)
        commands.run('mountpoint', ['/usr/bin/mountpoint', '-q', str(WORK / 'scratch')]); label, _ = commands.run('scratch-label', ['/usr/bin/findmnt', '-n', '-o', 'LABEL', '--target', str(WORK / 'scratch')]); require(label == b'mckernel-scratch\n', 'scratch label')
        require({path: Path(path).read_text().strip() for path in CGROUP} == CGROUP, 'exact cgroup')
        image_raw, image_id = regular(WORK / 'logs/image-native.json', 4 * 1024 * 1024); require(image_id['sha256'] == IMAGE_MANIFEST_SHA, 'image manifest'); retained_image = strict_json(image_raw)[0]; require(retained_image.get('Id') == IMAGE_ID, 'image manifest ID')
        raw, _ = commands.run('image-inspect', [DOCKER, 'image', 'inspect', IMAGE_ID]); image = base.one_inspect(raw); require(image.get('Config') == retained_image.get('Config') and image.get('RootFS') == retained_image.get('RootFS'), 'immutable image Config/RootFS')
        create = expected_create(nonce, mount); save(host / 'create-argv.json', {'argv': create, 'application_acceptance': False}); result['create_submitted_monotonic'] = time.monotonic(); created, _ = commands.run('create', create); require(re.fullmatch(rb'[0-9a-f]{64}\n', created), 'full container ID')
        config.update(container_id=created[:-1].decode('ascii'), orchestrator_sha256=base.ORCHESTRATOR_SHA, deadline_monotonic=time.monotonic() + 300); config['disarm'] = 'DISARM ' + nonce + ' ' + config['container_id'] + '\n'; write(host / 'watchdog-config.json', (json.dumps(config, sort_keys=True, allow_nan=False) + '\n').encode())
        row = lookup(commands, config, 'before-start'); require(row is not None and row['State']['Status'] == 'created' and row['State']['Running'] is False, 'created state'); full_inspect(row, config, image, retained_image); compiler_copies(commands, config, host)
        read_fd, control = os.pipe2(os.O_CLOEXEC); out = os.open(host / 'watchdog.stdout.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600); err = os.open(host / 'watchdog.stderr.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        try: watch = subprocess.Popen([PYTHON, '-I', '-B', str(host / 'root_orchestrator.py'), '--watchdog', str(host / 'watchdog-config.json'), str(read_fd), str(lock_fd)], stdin=subprocess.DEVNULL, stdout=out, stderr=err, env={}, close_fds=True, pass_fds=(read_fd, lock_fd), start_new_session=True)
        finally: os.close(read_fd); os.close(out); os.close(err)
        deadline = time.monotonic() + 5
        while not (host / 'watchdog-ready.json').exists() and time.monotonic() < deadline: require(os.waitid(os.P_PID, watch.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None, 'watchdog early exit'); time.sleep(0.01)
        ready = strict_json(regular(host / 'watchdog-ready.json')[0]); actual = supervisor._process_identity(watch.pid); require(ready['pid'] == watch.pid and ready['subreaper'] is True and ready['deadline_monotonic'] == config['deadline_monotonic'] and ready['lock_identity'] == stat_identity(lock_fd) and actual['ppid'] == os.getpid() and actual['pgid'] == actual['session'] == watch.pid, 'private watchdog identity'); result['watchdog_process'] = actual
        _, attached = commands.run('start-attach', [DOCKER, 'start', '--attach', config['container_id']], config['deadline_monotonic'] - time.monotonic()); require(attached['payload_completion_observed_monotonic'] < config['deadline_monotonic'], 'owner deadline')
        row = lookup(commands, config, 'after-exit'); require(row is not None and row['State']['Status'] == 'exited' and row['State']['ExitCode'] == 0 and row['State']['Error'] == '', 'normal candidate exit'); full_inspect(row, config, image, retained_image)
        manifest, identity = verify_result(mount, host, input_hashes); result.update(collected_infrastructure_candidate=True, harness_manifest_sha256=identity['sha256'], harness_status=manifest['status'])
    except BaseException as error:
        result['first_failure'] = {'type': type(error).__name__, 'message': str(error)}; first_failure(host, 'owner', error); save(host / 'owner-error.json', {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()})
    finally:
        if commands is not None and result.get('create_submitted_monotonic') is not None:
            try: result['cleanup'] = reviewed_owner().recover_cleanup(commands, config, 'owner-final')
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'cleanup', error)
        if control is not None and result.get('cleanup', {}).get('absence_verified') is True:
            try: os.write(control, config['disarm'].encode())
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'disarm', error)
        if control is not None: os.close(control)
        if watch is not None:
            try:
                end = time.monotonic() + 210
                while time.monotonic() < end:
                    pid, raw = os.waitpid(watch.pid, os.WNOHANG)
                    if pid: result['watchdog_raw_wait_status'] = raw; break
                    time.sleep(0.05)
                require(result['watchdog_raw_wait_status'] == 0 and strict_json(regular(host / 'watchdog-result.json')[0]).get('status') == 'DISARMED_AFTER_VERIFIED_ABSENCE', 'watchdog disarm')
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'watchdog-reap', error)
        try: save(host / 'original-tree-inventory.json', {'trees': [reviewed_owner().inventory(host)] + ([reviewed_owner().inventory(mount)] if mount.exists() else []), 'ownership_changed': False, 'root_owned_output_preserved': True, 'application_acceptance': False})
        except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'inventory', error)
        cleanup = result.get('cleanup', {})
        if result.get('collected_infrastructure_candidate') is True and not result.get('first_failure') and not result['diagnostic_errors'] and not (host / 'first-failure.json').exists() and cleanup.get('absence_verified') is True and cleanup.get('evidence_complete') is True and cleanup.get('first_failure') is None and result.get('watchdog_raw_wait_status') == 0: result['status'] = 'PASS_PENDING_FREE_BATCH_BUILD_OWNER_INFRASTRUCTURE_ONLY'
        result['finished_monotonic'] = time.monotonic(); save(host / 'result.json', result)
        if cleanup.get('absence_verified') is True and result.get('watchdog_raw_wait_status') == 0: os.close(lock_fd)
    print(result['status'] + ' ' + str(host), flush=True); return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
