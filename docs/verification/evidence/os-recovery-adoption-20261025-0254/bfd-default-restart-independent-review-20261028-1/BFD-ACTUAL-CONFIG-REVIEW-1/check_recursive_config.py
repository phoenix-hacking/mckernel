"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure configured-dependency consumer check; no guard, account or observation call.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import os
import resource
import tempfile

os.sched_setaffinity(0, {0})
resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
O = Path(__file__).resolve().parent
E = O.parents[1]
D = E / 'bfd-default-control-routing-restart-20261028-1/entry'
R = E / 'restart-adoption-20261028T1911/BFD-FINAL-INTEGRATION-1'

def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def checked(row):
    assert ref(row['path']) == row
    return json.loads(Path(row['path']).read_bytes())

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

physical_ref = ref(R / 'PHYSICAL-HISTORY-CONFIG.ACTUAL.json')
assert physical_ref['bytes'] == 6241
assert physical_ref['sha256'] == '1ad82f2b127e52867b65f3ed60f742878e3aba47b37e40168ae4e45a9dc13f02'
physical = checked(physical_ref)
guard_config_ref = ref(R / 'GUARD-FACADE-CONFIG.ACTUAL.json')
assert guard_config_ref['sha256'] == '0a1550ca5de876e7bc57db54350ffc046dc0e31c615b7b52c20b525bf80b1dc5'
assert physical['author'] == '/root' and physical['runtime_authority'] is None
assert physical['guard_config'] == guard_config_ref
assert physical['guard_adapter'] == ref(D / 'bfd_guard_facade.py')
assert physical['independent_review'] == ref(O / 'PHYSICAL-CONFIG-REVIEW.json')
assert physical['independent_review']['sha256'] == 'd5f6c442899136184f06eacb40227c81854efc0ee2cc2502ce009975e3445705'
common_review = json.loads((D / 'COMMON-DEPENDENCY-REVIEW.TEMPLATE.NOT-A-PASS.json').read_bytes())
common_review.update(TEST_ONLY=True, independent=True, implementation_ownership=False,
                    reviewer='/root/bfd_review', decision=common_review['required_decision'],
                    reviewed_account_window_guard_configuration=guard_config_ref,
                    reviewed_physical_history_configuration=physical_ref)
common = load('BFD_pure_recursive_common', D / 'observe_bfd_root59_history.py')
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_recursive_BFD_', dir=O) as tmp:
    review_path = Path(tmp) / 'TEST_ONLY_COMMON_REVIEW.json'
    review_path.write_text(json.dumps(common_review))
    bindings = dict(schema='mckernel.configured-root59-observer-dependencies.v1',
        author='/root', observer=ref(D / 'observe_bfd_root59_history.py'),
        nonce_ledger=common.CURRENT['ledger'], account_window_guard=physical['guard_adapter'],
        account_window_guard_configuration=guard_config_ref,
        physical_history_observer=physical['successor_source'],
        physical_history_configuration=physical_ref,
        independent_dependency_review=ref(review_path), runtime_authority=None)
    guard, history = common.configured_dependencies(bindings)
    assert guard.binding() == checked(guard_config_ref)
    assert history.binding() == physical
    recursive_guard = history.guard_module()  # configure only; no guard invocation.
    assert recursive_guard.binding() == guard.binding()
    assert recursive_guard.current_cutoffs() == [1793253600, 1035704.5689393478, 1051042.6959879305]

top = load('BFD_pure_recursive_top', D / 'observe_bfd_current61.py')
mid_ref = top.PINS['current60_source']
mid = load('BFD_pure_recursive_middle', mid_ref['path'])
assert ref(mid_ref['path']) == mid_ref
assert mid.PINS['common'] == ref(D / 'observe_bfd_root59_history.py')
# Only the local configured-dependency file is read by current60 observe(), never
# its historical CURRENT116 dependency reference retained as provenance in PINS.
mid_tree = ast.parse(Path(mid_ref['path']).read_bytes())
observe = next(n for n in mid_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'observe')
dep = next(n.value for n in observe.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == 'dependencies' for t in n.targets))
assert ast.unparse(dep) == "json.loads((HERE / 'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json').read_bytes())"
top_template = json.loads((D / 'TOP-DEPENDENCY-REVIEW.TEMPLATE.NOT-A-PASS.json').read_bytes())
assert top_template['observer'] == ref(D / 'observe_bfd_current61.py')
assert top_template['guard_adapter'] == physical['guard_adapter']
assert top.CURRENT['ledger']['sha256'] == '20e2470a6f7f81b188350af1374611801f68eacbf80ee8916814bd48962f4fa2'
print(json.dumps(dict(status='PASS_EXACT_BFD_RECURSIVE_CONFIGURED_SOURCE_CHAIN_ONLY',
    actual_physical_config=physical_ref, configured_common_physical_and_recursive_guard=True,
    top_current60_common_local_edges=True, live_guard_account_capture_calls=0,
    temporary_TEST_ONLY_review_removed=True, runtime_authority=None), indent=2))
