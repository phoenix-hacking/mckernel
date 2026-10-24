"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation ONLY: no subprocess, import of runtime, fixture, or native action.
Run once with a root-authored JSON config after the new capsule/manifest exists.
Preserves every original file and refuses an existing successor destination.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/qmp-runtime-successor-1')
SEG = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/cumulative-continuation-90s')
OUT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/continuation-review/runtime-successor-2')
COLLECTOR = OUT.parent / 'collector-source720'
STAGE_LOADER = OUT.parent / 'strict-v2-loader-source'
NAMES = ('native_diagnostic.py', 'native_diagnostic_runner.py',
         'native_diagnostic_backend.py', 'native_diagnostic_container_owner.py',
         'qmp_capture.py', 'repaired_image_authority.py', 'composite_module_binding.py',
         'p12_long_session.py', 'long_transport.py')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def need(ok, why):
    if not ok:
        raise ValueError(why)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def assignment(source, name):
    tree = ast.parse(source)
    rows = [n for n in tree.body if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    need(len(rows) == 1, 'one source assignment: ' + name)
    return ast.literal_eval(rows[0].value)

def replace_assignment(source, name, value):
    pattern = r'^' + re.escape(name) + r' = .*$'
    result, count = re.subn(pattern, name + ' = ' + repr(value), source, flags=re.M)
    need(count == 1, 'one replacement: ' + name)
    return result

def main():
    if sys.argv[1:] == ['--stage-loader-only']:
        need(not STAGE_LOADER.exists(), 'fresh strict v2 staging loader only')
        selected = ('native_diagnostic.py', 'long_transport.py',
                    'composite_module_binding.py', 'repaired_image_authority.py',
                    'CURRENT68-SDK8-AUTHORITY-LINKS.json', 'p12_long_session.py')
        values = {name: (BASE / 'source' / name).read_bytes() for name in selected}
        originals = {name: sha(raw) for name, raw in values.items()}
        transport = values['long_transport.py'].decode()
        old_profile = 'version=1, work_ns=3600000000000, wall_ns=7200000000000,\n               min_launches=100'
        need(transport.count(old_profile) == 1, 'exact accepted v1 transport source')
        transport = transport.replace(old_profile, 'version=2, work_ns=90000000000, wall_ns=600000000000,\n               min_launches=2')
        need(transport.count('inner_seconds=7800, outer_seconds=8100') == 1, 'exact accepted transport budgets')
        transport = transport.replace('inner_seconds=7800, outer_seconds=8100', 'inner_seconds=1200, outer_seconds=1500')
        # No owner/request/output namespace is authorized before actual capsule.
        # The existing validate_release mandatory non-null gate stays intact.
        transport = replace_assignment(transport, 'EXTERNAL_CAPTURE_BINDING', None)
        values['long_transport.py'] = transport.encode()
        values['p12_long_session.py'] = (SEG / 'p12_cumulative_segment.py').read_bytes()
        for name, raw in values.items():
            if name.endswith('.py'):
                ast.parse(raw, filename=name)
        STAGE_LOADER.mkdir()
        for name, raw in values.items():
            (STAGE_LOADER / name).write_bytes(raw)
        handoff = dict(scope=SCOPE, status='STRICT_V2_LOADER_SOURCE_ONLY_NO_STAGE_TEST_NATIVE_OR_EXECUTION_RELEASE',
            diagnostic_source=str(STAGE_LOADER / 'native_diagnostic.py'),
            callable='load_manifest', parent=str(BASE / 'source'),
            accepted_source_sha256=originals,
            source_sha256={name: sha(raw) for name, raw in values.items()},
            changes={'long_transport.py': 'exact v2/90s/600s/min2 profile;1200/1500 host budgets;capture bindingNone fails existing release gate',
                     'p12_long_session.py': 'supplied derived strict v2 segment consumer'},
            unchanged=['native_diagnostic.py', 'composite_module_binding.py',
                       'repaired_image_authority.py', 'CURRENT68-SDK8-AUTHORITY-LINKS.json'],
            retained_guards='load_manifest native body byte-identical: all JSON, artifact, exact final-map, SDK8 module, current kernel/launcher, source/native/physical authority checks retained.',
            runtime_owner=None, sourcehash_owner_map=None, execution_release=None,
            next='Capsule owner can set diagnostic_source to this path before capsule exists. After actual v2 capsule/manifest, config mode refreezes full runtime cohort and root independently admits its exact release.')
        (STAGE_LOADER / 'STRICT-V2-LOADER.SOURCE-HANDOFF.json').write_text(json.dumps(handoff, indent=2) + '\n')
        return
    if sys.argv[1:] == ['--collector-source-only']:
        need(not COLLECTOR.exists(), 'fresh collector successor only')
        values = {p.name: p.read_bytes() for p in (SEG / 'source').iterdir() if p.is_file()}
        old = b'#define COLLECTOR_SECONDS 7320u'
        need(values['pair_collector.c'].count(old) == 1, 'exact old collector outer budget')
        values['pair_collector.c'] = values['pair_collector.c'].replace(old, b'#define COLLECTOR_SECONDS 720u')
        COLLECTOR.mkdir()
        for name, raw in values.items():
            (COLLECTOR / name).write_bytes(raw)
        (COLLECTOR / 'SOURCE-ONLY.NOT-RELEASED.json').write_text(json.dumps(dict(
            scope=SCOPE, status='SOURCE_ONLY_NO_COMPILE_TEST_OR_NATIVE_ACCEPTANCE',
            parent=str(SEG / 'source'), source_sha256={name: sha(raw) for name, raw in values.items()},
            correction='ND_PAIR_LONG outer guest collector 7320 to720 seconds, preserving120s startup/teardown allowance; Rust/bridge600s unchanged.'), indent=2) + '\n')
        return
    need(len(sys.argv) == 2, 'config JSON path required')
    cfg = json.loads(Path(sys.argv[1]).read_bytes())
    need(set(cfg) == {'manifest_path', 'manifest_sha256', 'release_path', 'nonce',
                     'host_parent', 'retention_parent', 'host_device',
                     'scratch_backing_bytes', 'extra_readonly', 'extra_source_sha256'},
         'exact config keys')
    need(not OUT.exists(), 'fresh successor only')
    for key in ('manifest_path', 'release_path', 'host_parent', 'retention_parent'):
        need(Path(cfg[key]).is_absolute(), 'absolute ' + key)
    need(re.fullmatch('[0-9a-f]{32}', cfg['nonce']) is not None, 'fresh nonce spelling')
    need(Path(cfg['manifest_path']).read_bytes() and
         sha(Path(cfg['manifest_path']).read_bytes()) == cfg['manifest_sha256'],
         'actual successor manifest pin')
    need(cfg['host_parent'] != '/home/holden/mckernel-work/l12q1/p' and
         cfg['manifest_path'] != '/home/holden/mckernel-work/scratch/p12q1/m.json' and
         cfg['release_path'] != '/home/holden/mckernel-work/scratch/p12q1/r.json',
         'fresh output/manifest/release namespace')
    need(type(cfg['host_device']) is int and type(cfg['scratch_backing_bytes']) is int and
         cfg['scratch_backing_bytes'] in (110 * 2**30, 142 * 2**30), 'reviewed storage identities')
    sources = {name: (BASE / 'source' / name).read_text() for name in NAMES}
    originals = {name: sha(value.encode()) for name, value in sources.items()}
    newroot = str(OUT / 'source')
    owner_path = newroot + '/native_diagnostic_container_owner.py'
    wrapper_path = str(OUT / 'capture_root_SEGMENT.NOT-RELEASED.py')
    wrapper = (BASE / 'capture_root_LONG.NOT-RELEASED.py').read_text()
    for name, value in {'OWNER_PATH': owner_path, 'RELEASE_PATH': cfg['release_path'],
                        'HOST_PARENT': cfg['host_parent'], 'NONCE': cfg['nonce'],
                        'MANIFEST_PATH': cfg['manifest_path'], 'MANIFEST_SHA': cfg['manifest_sha256']}.items():
        wrapper = replace_assignment(wrapper, name, value)
    need(wrapper.count("r['soft_wall_seconds']==8100") == 1, 'old wrapper softwall')
    wrapper = wrapper.replace("r['soft_wall_seconds']==8100", "r['soft_wall_seconds']==1500")
    transport = sources['long_transport.py']
    need('version=1, work_ns=3600000000000, wall_ns=7200000000000,\n               min_launches=100' in transport,
         'old exact producer profile')
    transport = transport.replace('version=1, work_ns=3600000000000, wall_ns=7200000000000,\n               min_launches=100',
                                  'version=2, work_ns=90000000000, wall_ns=600000000000,\n               min_launches=2')
    need(transport.count('inner_seconds=7800, outer_seconds=8100') == 1, 'old exact host budgets')
    transport = transport.replace('inner_seconds=7800, outer_seconds=8100', 'inner_seconds=1200, outer_seconds=1500')
    transport = replace_assignment(transport, 'HOST_OUTPUT', dict(
        schema='mckernel.p12.host-output.v1', parent=cfg['host_parent'],
        retention_parent=cfg['retention_parent'], device=cfg['host_device'],
        uid=1000, gid=1000, mode=448, scratch_output_bytes=0))
    capture = assignment(transport, 'EXTERNAL_CAPTURE_BINDING')
    capture.update(controller_path=wrapper_path, controller_sha256=sha(wrapper.encode()),
                   request_path=str(OUT / 'CAPTURE-REQUEST.json'),
                   capture_directory=str(OUT / 'actual-capture-1'),
                   command_source_path=owner_path, soft_wall_seconds=1500)
    transport = replace_assignment(transport, 'EXTERNAL_CAPTURE_BINDING', capture)
    need(transport.count('info.st_size == 110 * 2**30') == 1, 'old exact backing size')
    transport = transport.replace('info.st_size == 110 * 2**30', 'info.st_size == ' + str(cfg['scratch_backing_bytes']))
    transport = transport.replace('exact110GiB host sparse backing', 'exact reviewed host sparse backing')
    sources['long_transport.py'] = transport
    # Existing consumer filename is the actual native_diagnostic dynamic import.
    sources['p12_long_session.py'] = (SEG / 'p12_cumulative_segment.py').read_text()
    owner = sources['native_diagnostic_container_owner.py']
    oldroot = str(BASE / 'source')
    # Includes RUNNER, SELF, and bound_manifest's absolute diagnostic import.
    owner = owner.replace(oldroot, newroot)
    readonly = assignment(owner, 'EXTRA_READONLY')
    readonly.extend([str(OUT), str(SEG), str(COLLECTOR), *cfg['extra_readonly']])
    owner = replace_assignment(owner, 'EXTRA_READONLY', sorted(set(readonly)))
    hashes = assignment(owner, 'SOURCE_HASHES')
    for name in NAMES:
        if name != 'native_diagnostic_container_owner.py':
            hashes[newroot + '/' + name] = sha(sources[name].encode())
    # Remap only cohort entries. Original other artifact/source pins stay intact.
    for path, digest in cfg['extra_source_sha256'].items():
        need(Path(path).is_absolute() and sha(Path(path).read_bytes()) == digest,
             'actual extra source/artifact pin: ' + path)
        hashes[path] = digest
    owner = replace_assignment(owner, 'SOURCE_HASHES', hashes)
    sources['native_diagnostic_container_owner.py'] = owner
    # Parse only; do not import or execute any reviewed runtime source.
    for name, value in sources.items():
        ast.parse(value, filename=name)
    ast.parse(wrapper, filename=wrapper_path)
    (OUT / 'source').mkdir(parents=True)
    for name, value in sources.items():
        (OUT / 'source' / name).write_text(value)
    authority = 'CURRENT68-SDK8-AUTHORITY-LINKS.json'
    (OUT / 'source' / authority).write_bytes((BASE / 'source' / authority).read_bytes())
    Path(wrapper_path).write_text(wrapper)
    (OUT / 'SOURCE-PREPARATION.NOT-RELEASED.json').write_text(json.dumps(dict(
        scope=SCOPE, status='SOURCE_ONLY_NOT_RUNTIME_PASS_NOT_EXECUTION_RELEASE',
        accepted_source_sha256=originals, successor_source_sha256={
            name: sha(value.encode()) for name, value in sources.items()},
        wrapper_sha256=sha(wrapper.encode()), config=cfg,
        budgets=dict(guest_collector_seconds=720, producer_seconds=600,
                     inner_seconds=1200, outer_seconds=1500),
        remaining='Root constructs exact release/source cohort, independent review, fresh boot/storage admission and CAPTURE-REQUEST with actual owner digest + release digest. No execution authority is produced here.'), indent=2) + '\n')

if __name__ == '__main__':
    main()
