"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure additive source/dependency composition. No guard, nonce, capture or workload.
"""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
E = HERE.parent.parent
OLD60 = E/'current116-actual-postjoin-current60-source-20261028-1'
OLD61 = OLD60/'current61-after116-consumer-source-1/consumer-physical-shape-correction-source-1'
OLDF = OLD61/'finalizer-window-clamp-correction-source-1/root-adopted-process227-entry-1'
OLDC = E/'original227-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/revision2'
SHARED = E/'restart-operation-guard-source-20261028-1/operation_window_guard.py'
GUARDIAN = E/'restart-operation-guard-source-20261028-1/guardian_guard.py'
LIMITS = [1793253600, 1035704.5689393478, 1051042.6959879305]
NAMES = ['prepare_startup_bindings.py', 'bind_startup_resource.py',
         'run_startup_resource_once.py', 'capture_fresh_startup_resource.py',
         'run_native_startup_capture.py', 'runtime_guard.py']


def ref(p):
    p = Path(p); raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(p):
    return json.loads(Path(p).read_bytes())


def create(p, value):
    p = Path(p)
    with p.open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True); out.write('\n')


def source(p, text):
    ast.parse(text)
    with Path(p).open('x') as out:
        out.write(text)


def prepare(destination):
    """Only source files and explicitly unauthoritative DATA templates are produced."""
    d = Path(destination).resolve()
    d.mkdir(parents=True, exist_ok=True)
    common = d/'common'; current60 = d/'current60'; current61 = d/'current61'
    entry = d/'root-adopted-process227-entry-1'
    for p in (common, current60, current61, entry):
        p.mkdir(exist_ok=False)
    changes = []

    def copy_source(old, new, replacements=()):
        before = old.read_text(); after = before
        for previous, successor in replacements:
            assert after.count(previous) >= 1, (old, previous)
            after = after.replace(previous, successor)
        source(new, after)
        changes.append(dict(previous=ref(old), successor=ref(new),
                            replacements=[dict(previous=a, successor=b) for a,b in replacements],
                            diff=''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                           fromfile=str(old), tofile=str(new)))))

    copy_source(OLDC/'observe_root59_configured.py', common/'observe_root59_configured.py')
    copy_source(OLD60/'observe_current60_postjoin.py', current60/'observe_current60_postjoin.py')
    copy_source(OLD61/'observe_current61_original227.py', current61/'observe_current61_original227.py',
                [(str(OLD60/'observe_current60_postjoin.py'), str(current60/'observe_current60_postjoin.py'))])
    observer = ref(current61/'observe_current61_original227.py')
    schema = read(OLD61/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json'); schema['observer'] = observer
    create(current61/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json', schema)
    for name in NAMES:
        replacements = []
        if str(OLDF) in (OLDF/name).read_text():
            replacements.append((str(OLDF), str(entry)))
        if name == 'capture_fresh_startup_resource.py':
            previous = repr(ref(OLD61/'observe_current61_original227.py'))
            replacements.append((previous, repr(observer)))
        if name == 'prepare_startup_bindings.py':
            replacements.append(('STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',
                                 'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'))
        copy_source(OLDF/name, entry/name, replacements)
    bridge = (OLDF/'root_once_startup_entry.py').read_text()
    bridge = bridge.replace(str(OLDF.parent), str(d)).replace(str(OLDF), str(entry))
    bridge = bridge.replace("STATIC_SHA = '94d1ef8483c15aa2838227ccc5daf65ad537d5fed6d262fcd7f66693b072e590'",
                            "STATIC_SHA = 'ROOT_FINAL_RESTART_STATIC_SHA256'")
    bridge = bridge.replace("HELPER_SHA = '7e71518071dc52287be497c8f0cf15f45ffeb5df55ad3f4b1b4eac1608497963'",
                            'HELPER_SHA = '+repr(ref(entry/'run_native_startup_capture.py')['sha256']))
    source(entry/'root_once_startup_entry.TEMPLATE.NOT-AUTHORITY.py', bridge)
    changes.append(dict(previous=ref(OLDF/'root_once_startup_entry.py'),
                        successor=ref(entry/'root_once_startup_entry.TEMPLATE.NOT-AUTHORITY.py'),
                        allowed_changes=['BASE/path hardpins', 'STATIC_SHA final composition slot', 'HELPER_SHA source hardpin'],
                        diff=''.join(difflib.unified_diff((OLDF/'root_once_startup_entry.py').read_text().splitlines(True),
                                                       bridge.splitlines(True), fromfile=str(OLDF/'root_once_startup_entry.py'),
                                                       tofile=str(entry/'root_once_startup_entry.TEMPLATE.NOT-AUTHORITY.py')))))
    pins = read(OLD60/'ACTUAL-PINS.json')
    pins['common'] = ref(common/'observe_root59_configured.py')
    pins['common_dependencies'] = None
    create(current60/'ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json', pins)
    deps = read(OLDC/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json')
    deps.update(author=None, observer=pins['common'], independent_dependency_review=None,
                account_window_guard_configuration=None, physical_history_configuration=None)
    create(common/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json', deps)
    root61 = dict(author=None, observer=observer,
                  ledger=read(OLDF/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json')['root_ledger35'],
                  guard_adapter=deps['account_window_guard'], guard_configuration=None,
                  independent_review=None, runtime_authority=None)
    create(current61/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json', root61)
    facade = read(OLDC/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.TEMPLATE.NOT-AUTHORITY.json')
    facade.update(author=None, runtime_facade=ref(entry/'runtime_guard.py'), configuration=None, independent_review=None)
    create(entry/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.TEMPLATE.NOT-AUTHORITY.json', facade)
    static = read(OLDF/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json')
    static.update(author=None, runtime_authority=None, status='RESTART_SOURCE_TEMPLATE_NOT_RUNTIME_AUTHORITY',
                  fixed_cutoffs=LIMITS, current_observer_source=observer,
                  current_observer_schema=ref(current61/'OBSERVER-SCHEMA.ROOT61.SOURCE-ONLY.json'),
                  current_observer_source_review=None, source_authority=None, case_capability=None,
                  stage_map_acceptance=None, source_only_QMPproof=None,
                  capture_sources={n:ref(entry/n) for n in NAMES if n != 'runtime_guard.py'},
                  capture_helper=ref(entry/'run_native_startup_capture.py'), capture_directory=str(entry/'CAPTURE'),
                  root_admission_directory=str(entry), retained_predecessor_static=ref(OLDF/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'))
    # The old sealing binding is historical provenance, not this successor's live configuration.
    static['historical_original227_source_sealing_binding'] = static.pop('new_original227_sealing_window_binding')
    create(entry/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json', static)
    create(d/'EXACT-SOURCE-DELTAS.json', dict(scope=__doc__.splitlines()[0], changes=changes,
                                            physical_history_source_reused=ref(E/'new-window-physical-history-successor-source-20261028-1/physical_history_successor.py'),
                                            new_shared_guard=ref(SHARED), new_guardian=ref(GUARDIAN),
                                            runtime_authority=None))
    return dict(common=common, current60=current60, current61=current61, entry=entry)


def compose(root_inputs, destination):
    """Root-only metadata fill, with no nonce reservation/rebinding or runtime action."""
    q = read(root_inputs)
    assert q['author'] == '/root' and q['decision'] == 'COMPOSE_RESTART_ORIGINAL227_SOURCE_ONLY'
    assert q['runtime_authority'] is None and q['preserve_reserved_nonce_without_replaying_nonce_binding'] is True
    d = Path(destination).resolve(); entry=d/'root-adopted-process227-entry-1'
    assert q['source_delta_manifest'] == ref(d/'EXACT-SOURCE-DELTAS.json')
    for key in ['current_observer_source_review', 'source_authority', 'case_capability', 'stage_map_acceptance']:
        assert ref(q[key]['path']) == q[key]
    static=read(entry/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')
    static.update(author='/root', status='RESTART_SOURCE_COMPOSED_NOT_RUNTIME_RELEASED')
    for key in ['current_observer_source_review','source_authority','case_capability','stage_map_acceptance']:
        static[key]=q[key]
    static['source_only_QMPproof']=q['stage_map_acceptance']
    # Runtime configs/reviews are external DATA. Embedding root_inputs here would
    # create static -> inputs -> dependencies -> config -> operation -> static.
    create(entry/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',static)
    bridge=(entry/'root_once_startup_entry.TEMPLATE.NOT-AUTHORITY.py').read_text()
    bridge=bridge.replace('ROOT_FINAL_RESTART_STATIC_SHA256',ref(entry/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json')['sha256'])
    source(entry/'root_once_startup_entry.py',bridge)
    return dict(static=ref(entry/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),bridge=ref(entry/'root_once_startup_entry.py'),runtime_authority=None)


def bind_dependencies(root_inputs,destination):
    """External runtime DATA is bound after static/source subjects and config review."""
    q=read(root_inputs);d=Path(destination).resolve();entry=d/'root-adopted-process227-entry-1'
    assert q['author']=='/root' and q['decision']=='BIND_RESTART_ORIGINAL227_DEPENDENCIES_SOURCE_ONLY'
    assert q['runtime_authority'] is None and q['source_delta_manifest']==ref(d/'EXACT-SOURCE-DELTAS.json')
    for key,path in [('common_dependencies',d/'common/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'),
                     ('root61_dependencies',d/'current61/ROOT61-RUNTIME-DEPENDENCIES.json'),
                     ('facade_binding',entry/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json')]:
        assert q[key]['path']==str(path) and ref(path)==q[key]
    pins=read(d/'current60/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json');pins['common_dependencies']=q['common_dependencies']
    create(d/'current60/ACTUAL-PINS.json',pins)
    return dict(current60_pins=ref(d/'current60/ACTUAL-PINS.json'),runtime_authority=None)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--prepare-source',action='store_true');mode.add_argument('--bind-dependencies',action='store_true')
    p.add_argument('--root-inputs',type=Path)
    p.add_argument('--root-inputs-sha256');p.add_argument('--destination',required=True,type=Path);a=p.parse_args()
    if a.prepare_source:
        assert not a.root_inputs
        print(json.dumps({k:str(v) for k,v in prepare(a.destination).items()}))
    else:
        assert a.root_inputs and ref(a.root_inputs)['sha256']==a.root_inputs_sha256
        print(json.dumps((bind_dependencies if a.bind_dependencies else compose)(a.root_inputs,a.destination)))
