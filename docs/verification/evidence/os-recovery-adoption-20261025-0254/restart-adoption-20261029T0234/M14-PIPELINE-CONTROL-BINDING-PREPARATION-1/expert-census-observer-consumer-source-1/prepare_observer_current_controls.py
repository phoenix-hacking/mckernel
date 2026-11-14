"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical source/data constructor only. Never imports guardian or cleanup modules.
"""
import argparse
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path


# Exact pure finite-cutoff helper; source construction only, never runtime admission.
import importlib.util as _cutoff_import
CUTOFF_SOURCE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/cutoff_bindings.py', 'bytes': 1625, 'sha256': '0c3c71e918a131b2ae3a3a7cc4aba7014af602dc6bed5704e58af69add118998'}
_cutoff_raw = Path(CUTOFF_SOURCE['path']).read_bytes()
assert len(_cutoff_raw)==CUTOFF_SOURCE['bytes'] and hashlib.sha256(_cutoff_raw).hexdigest()==CUTOFF_SOURCE['sha256'], 'exact cutoff helper bytes'
_cutoff_spec = _cutoff_import.spec_from_file_location('m14_pure_cutoff_bindings',CUTOFF_SOURCE['path'])
CUTOFF = _cutoff_import.module_from_spec(_cutoff_spec)
_cutoff_spec.loader.exec_module(CUTOFF)

HERE = Path(__file__).resolve().parent
BASE = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
SOURCE2 = BASE / 'CURRENT118-postbuild-current-successor-preparation-1/source-2'
SOURCE1 = BASE / 'CURRENT118-postbuild-current-successor-preparation-1/source-1'
ACTUAL = BASE / 'restart-adoption-20261029T0234'
NEWSC = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1')
STATE = Path('/home/holden/mckernel/.git/os-autopilot/state.json')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PINS = {
    'observer': (SOURCE2 / 'observe_current64_current118_postjoin.py', 'd216adacf568e3e13c70bc8877a0e6a5af6713dad0c60044b03b87091e03ecfd'),
    'inputs': (SOURCE2 / 'INPUTS.json', '4bd01a601ff4a8293da6a59955da79dfde6f37ab0963b95202dd49425f00a71a'),
    'shared_guard': (SOURCE1 / 'operation_window_guard64.py', '1d62a322620e24b8e25fb140eb60eda64c7356b3d5f1cdc616cc4b3c82e10db0'),
    'custody': (ACTUAL / 'ROOT-CUSTODY-SUPPLEMENT.ACTUAL.json', '90a0ccf3d1293697e21ee5e9bf0eb2244268eee84ffbf970990e7f69a0fe609a'),
    'ledger': (ACTUAL / 'ROOT-CURRENT-NONCE-LEDGER64.SUPPLEMENTED.PENDING.json', '3932659c13ba04997870e1d67b2a356b0205e699951a959dd6fdac4ddc7694ff'),
    'custody_validation': (ACTUAL / 'ACTUAL-CUSTODY-PURE-VALIDATION.json', 'b8e5be77b605fb69a8199d624cbda0b106667e3a8caa3bae793d298f5c3c4488'),
}
EXACT_CLEANUP = {'cleanup_executor': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1/retire_exact_current118_stopped_container.py', 'bytes': 45759, 'sha256': 'bec450e0f2a25f4624b83abf43338b424ce275d85193ae9f0caf3aedcb844f90'}, 'cleanup_bindings': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1/BINDINGS.json', 'bytes': 26741, 'sha256': 'feebbf1e0cecb7d6605d2e92f1288b969e5251419bb4d327c8b012d1221b97cd'}, 'cleanup_runtime_files': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1/RUNTIME-FILES.json', 'bytes': 3947, 'sha256': 'f367b012cba27dea8845771e4f77cdc39270c4c2f927fafa04abd31c650acaa7'}, 'cleanup_source_ready': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1/SOURCE_READY.json', 'bytes': 7857, 'sha256': '924c17f8044b7deac160fd06474bd7e15161f4ba5d6c003b1b7434bef468ac2c'}, 'cleanup_source_review': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1/independent-source-review-1/SOURCE-REVIEW.ACTUAL.json', 'bytes': 10526, 'sha256': 'cd4e215caf1995e819eb182f00583b49decf7a99115c0aaafcec476deb62ca44'}, 'expert_design': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/whole-snapshot-ENOENT-correction-source-1/independent-source-review-1/EXPERT-DESIGN.md', 'bytes': 5954, 'sha256': '125d29c7870755fa6f99970eb3d2c153800a801b04f8c25731fbc63312f9798c'}}
EXTRA_CUSTODY = {'post_root3_pending': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT-CURRENT-NONCE-LEDGER64.POST-ROOT3-FAILURE.PENDING.json', 'bytes': 42557, 'sha256': '5dea3b99e01f011e674f2bffb00730e1273f462bb9b8b0a51a857910d31fb8d4'}, 'post_root4_pending': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT-CURRENT-NONCE-LEDGER64.POST-ROOT4-RETIREMENT.PENDING.json', 'bytes': 43724, 'sha256': 'aefd078e282480715a4803cff9f46d3c71033616b91b950d8f0c9d5e9e888366'}, 'root4_parent_normalized': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/ACTUAL-RETIREMENT-ROOT4-PARENT/DIRECT-PARENT-JOIN.NORMALIZED.ACTUAL.json', 'bytes': 1616, 'sha256': '6a17cf3f4f923d42464c2741bd8b122261ed4de49519db3e091da56634b2e551'}, 'root4_parent_raw': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/ACTUAL-RETIREMENT-ROOT4-PARENT/DIRECT-PARENT-JOIN.ACTUAL.json', 'bytes': 2383, 'sha256': '2c4041377247ffedb960c8e38ddf5a7abf31777b2706330fd483a651c34bf805'}}
OBSERVER_TEMPLATE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/expert-census-observer-consumer-source-1/observe_current64_current118_postjoin.template.py', 'bytes': 45953, 'sha256': '124f9f04c295a205751865cba962c1394c909449d5a5495515717e2f12013b4a'}
FIELDS = {'schema','scope','guardian','guardian_review','armed_receipt','cleanup_executor','cleanup_bindings','cleanup_runtime_files','cleanup_source_ready','cleanup_source_review','thread_id'}

def need(ok, why):
    if not ok:
        raise ValueError(why)

def ref(path):
    path = Path(path)
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'absolute regular byte input')
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def auth(row):
    need(type(row) is dict and set(row) == {'path','bytes','sha256'}, 'exact byte reference')
    need(ref(row['path']) == row, 'exact unchanged input bytes')
    return Path(row['path'])

def checked(row):
    return json.loads(auth(row).read_bytes())

def contains(value, row):
    if value == row:
        return True
    if isinstance(value, dict):
        return any(contains(v, row) for v in value.values())
    if isinstance(value, list):
        return any(contains(v, row) for v in value)
    return False

def review_binds(value, rows):
    need(value.get('independent') is True and value.get('implementation_ownership') is False
         and str(value.get('decision','')).startswith('PASS'), 'independent reviewed source binding')
    need(all(contains(value, row) for row in rows), 'review authenticates every supplied source')

def rewrite_guard(source, guardian, thread_id):
    tree = ast.parse(source)
    old = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('GUARDIAN_SOURCE', 'THREAD', 'E'):
                old[node.targets[0].id] = node
    need(set(old) == {'GUARDIAN_SOURCE','THREAD','E'}, 'exact namespace and two shared guard assignments')
    lines = source.splitlines(True)
    for name, value in [('GUARDIAN_SOURCE', guardian), ('THREAD', thread_id), ('E', str(BASE))]:
        node = old[name]
        need(node.lineno == node.end_lineno, 'one-line exact source assignment')
        lines[node.lineno - 1] = name + ' = ' + ('Path(' + repr(value) + ')' if name == 'E' else repr(value)) + '\n'
    result = ''.join(lines)
    after = ast.parse(result)
    for before_node, after_node in zip(tree.body, after.body):
        if before_node not in old.values():
            need(ast.dump(before_node, include_attributes=False) == ast.dump(after_node, include_attributes=False), 'all account/window/clock/operation predicates unchanged')
    return result

def replace_refs(value, replacements):
    for before, after in replacements:
        if value == before:
            return copy.deepcopy(after)
    if isinstance(value, dict):
        return {key: replace_refs(v,replacements) for key,v in value.items()}
    if isinstance(value, list):
        return [replace_refs(v,replacements) for v in value]
    return value

def validate_cleanup(pins, manifest):
    old = checked(pins['retirement_bindings'])
    new = checked(manifest['cleanup_bindings'])
    need(set(old) == set(new), 'same cleanup bindings schema')
    for key in old:
        if key not in ('guardian','output_root_parent','cutoffs'):
            need(new[key] == old[key], 'unchanged cleanup boundary ' + key)
    CUTOFF.validate_monotone_cutoffs(old['cutoffs'],new['cutoffs'])
    need(new['guardian'] == manifest['guardian'], 'same actual new guardian in cleanup and observer')
    need(new['output_root_parent'] == str(Path(manifest['cleanup_executor']['path']).parent), 'cleanup output root matches its exact successor source directory')
    # Exact expert-reviewed successor only; never an AST/pattern allowance.
    for key in ('cleanup_executor','cleanup_bindings','cleanup_runtime_files','cleanup_source_ready','cleanup_source_review'):
        need(manifest[key] == EXACT_CLEANUP[key], 'exact independently reviewed monotone-census successor ' + key)
        auth(EXACT_CLEANUP[key])
    auth(EXACT_CLEANUP['expert_design'])
    review = checked(manifest['cleanup_source_review'])
    need(review['expert_design'] == EXACT_CLEANUP['expert_design'], 'exact expert design source')
    old_runtime = checked(pins['compatibility_runtime_files'])
    new_runtime = checked(manifest['cleanup_runtime_files'])
    expected_runtime = dict(old_runtime, executor=manifest['cleanup_executor'], bindings=manifest['cleanup_bindings'], guardian=manifest['guardian'])
    need(len(new_runtime) == 12 and new_runtime == expected_runtime, 'same12 cleanup runtime subjects, only3 exact reference successors')
    for row in new_runtime.values():
        auth(row)
    checked(manifest['cleanup_source_ready'])
    review_binds(checked(manifest['cleanup_source_review']), [manifest['cleanup_executor'],manifest['cleanup_bindings'],manifest['cleanup_runtime_files']])

def validate_manifest(manifest, pins):
    need(set(manifest) == FIELDS and manifest['schema'] == 'mckernel.current118.postjoin-control-source-inputs.v1'
         and manifest['scope'] == SCOPE, 'exact explicit source-only input manifest')
    for key in FIELDS - {'schema','scope','thread_id'}:
        auth(manifest[key])
    need(manifest['armed_receipt']['path'] == str(NEWSC / 'ACTUAL-CONTROLS-ARMED.json'), 'actual current arm receipt required')
    state = json.loads(STATE.read_bytes())
    need(manifest['thread_id'] == state['thread_id'] and manifest['thread_id'] != '01a183ec-72e5-7400-8f48-b4efb8725520', 'actual new launcher thread identity')
    budget = state['credit_budget']
    need(str(budget['id']) == '7f4af94a83b14cc08f97401f5891d965', 'same original cumulative credit run')
    need(manifest['guardian'] != pins['guardian'], 'new reviewed current guardian required')
    tree = ast.parse(auth(manifest['guardian']).read_bytes())
    need(any(isinstance(n, ast.FunctionDef) and n.name == 'guard' and not n.args.args for n in tree.body), 'existing no-argument guard API')
    review_binds(checked(manifest['guardian_review']), [manifest['guardian']])
    validate_cleanup(pins, manifest)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    supplied = ref(args.inputs)
    need(supplied['sha256'] == args.inputs_sha256, 'explicit immutable constructor input digest')
    refs = {}
    for key,(path,digest) in PINS.items():
        row = ref(path)
        need(row['sha256'] == digest, 'unchanged retained ' + key)
        refs[key] = row
    pins = checked(refs['inputs'])
    manifest = checked(supplied)
    validate_manifest(manifest,pins)
    old_observer = auth(refs['observer']).read_text()
    new_observer = auth(OBSERVER_TEMPLATE).read_text()
    for row in EXTRA_CUSTODY.values():
        auth(row)
    old_shared = auth(refs['shared_guard']).read_text()
    new_shared = rewrite_guard(old_shared,manifest['guardian'],manifest['thread_id'])
    outputs = ['observe_current64_current118_postjoin.py','operation_window_guard64.py','INPUTS.json','CONTROL-SOURCE-CONSTRUCTION.json','ROOT64-RUNTIME-BINDINGS.ACTUAL-CUSTODY.TEMPLATE.NOT-AUTHORITY.json','MINIMAL-DIFF.patch']
    need(not any((HERE/name).exists() for name in outputs), 'never overwrite existing materialization')
    # All authentication and scope checks precede first write. Exclusive creation
    # leaves any interrupted construction retained; this is never an execution grant.
    for name,text in [('observe_current64_current118_postjoin.py',new_observer),('operation_window_guard64.py',new_shared)]:
        with (HERE/name).open('x') as stream:
            stream.write(text)
    newpins = copy.deepcopy(pins)
    changes = dict(guardian=manifest['guardian'],shared_guard=ref(HERE/'operation_window_guard64.py'),retirement_source=manifest['cleanup_executor'],retirement_bindings=manifest['cleanup_bindings'],compatibility_runtime_files=manifest['cleanup_runtime_files'],compatibility_source_ready=manifest['cleanup_source_ready'])
    changes.update(EXTRA_CUSTODY)
    newpins.update(changes)
    with (HERE/'INPUTS.json').open('x') as stream:
        stream.write(json.dumps(newpins,indent=2)+'\n')
    binding = checked(ref(SOURCE2/'ROOT64-RUNTIME-BINDINGS.TEMPLATE.NOT-AUTHORITY.json'))
    binding.update(ledger=EXTRA_CUSTODY['post_root4_pending'],custody_supplement=refs['custody'],retirement_result=checked(EXTRA_CUSTODY['post_root4_pending']) and json.loads(checked(EXTRA_CUSTODY['post_root4_pending'])['note'])['closed_current118_root4_retirement']['result'],retirement_parent_join=EXTRA_CUSTODY['root4_parent_normalized'])
    with (HERE/'ROOT64-RUNTIME-BINDINGS.ACTUAL-CUSTODY.TEMPLATE.NOT-AUTHORITY.json').open('x') as stream:
        stream.write(json.dumps(binding,indent=2)+'\n')
    with (HERE/'MINIMAL-DIFF.patch').open('x') as stream:
        for old,new,name in [(old_observer,new_observer,'observe_current64_current118_postjoin.py'),(auth(refs['inputs']).read_text(),json.dumps(newpins,indent=2)+'\n','INPUTS.json'),(old_shared,new_shared,'operation_window_guard64.py')]:
            stream.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='retained/'+name,tofile='successor/'+name))
    receipt = dict(scope=SCOPE,status='SOURCE_ONLY_SUCCESSOR_REQUIRES_INDEPENDENT_REVIEW_NO_EXECUTION',runtime_authority=None,constructor_inputs=supplied,retained=refs,explicit_new_sources=manifest,observer=ref(HERE/'observe_current64_current118_postjoin.py'),inputs=ref(HERE/'INPUTS.json'),shared_guard=ref(HERE/'operation_window_guard64.py'),changed_INPUTS_fields=sorted(changes),changed_shared_guard_assignments=['E','GUARDIAN_SOURCE','THREAD'],observer_source_byte_identical=False,observer_template=OBSERVER_TEMPLATE,observer_independent_source_review=None,actual_custody=refs['custody'],actual_supplemented_pending_ledger=EXTRA_CUSTODY['post_root4_pending'],historical_pending_ledger_pin_unchanged=pins['pending_ledger'],original389_rejection_unchanged=True,compiler_guard_cleanup_proc_capture_calls=0)
    with (HERE/'CONTROL-SOURCE-CONSTRUCTION.json').open('x') as stream:
        stream.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
