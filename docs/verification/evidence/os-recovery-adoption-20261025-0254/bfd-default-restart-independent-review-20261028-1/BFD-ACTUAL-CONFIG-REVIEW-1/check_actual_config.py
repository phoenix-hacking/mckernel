"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/config binding checks. No guard(), observe(), account or capture calls.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource

os.sched_setaffinity(0, {0})
resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
E = Path(__file__).resolve().parents[2]
D = E / 'bfd-default-control-routing-restart-20261028-1'
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

config_path = R / 'GUARD-FACADE-CONFIG.ACTUAL.json'
assert ref(config_path)['sha256'] == '0a1550ca5de876e7bc57db54350ffc046dc0e31c615b7b52c20b525bf80b1dc5'
config = json.loads(config_path.read_bytes())
assert config['author'] == '/root' and config['operation'] == 'bfd-current-default-two-tools'
assert config['runtime_authority'] is None
binding = checked(config['operation_bindings'])
assert config['operation_bindings']['sha256'] == '80390c77c16466a3cbfe81a5c5a09f023e0142b91fbceb4c76e394650bf99fff'
assert binding['author'] == '/root' and binding['operation'] == config['operation']
assert binding['runtime_authority'] is None
operation = checked(binding['successor'])
review = checked(binding['independent_review'])
assert review['successor'] == operation
assert binding['successor']['sha256'] == '110ef6f3599a72f93a792a87f6cd7222126768780b6ec6f57bc9bf9db4b6a91f'
assert binding['independent_review']['sha256'] == 'e3cd2813067b0e9712ecbecf8efec64e2cc960eb0bb609c0b140fb91cea84089'
runtime = load('BFD_actual_config_runtime', config['runtime_guard']['path'])
assert ref(config['runtime_guard']['path']) == config['runtime_guard']
assert runtime.subjects() == binding['expected_subjects'] == operation['subjects']
assert len(binding['expected_subjects']) == 12
for row in binding['expected_subjects'].values():
    assert ref(row['path']) == row
shared = runtime.module()
# This is a declared fixture clock, never a fresh clock or account admission.
fixture_clocks = [1793216000, 997600, 1013000]
limits = shared.validate_operation(operation, review, runtime.OPERATION,
                                   binding['expected_subjects'], fixture_clocks, shared.BOOT)
assert list(limits) == config['authorized_clamps'] == [1793253600, 1035704.5689393478, 1051042.6959879305]
assert operation['guardian']['source']['sha256'] == '48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18'
facade = load('BFD_actual_config_facade', D / 'entry/bfd_guard_facade.py')
facade.configure(ref(config_path))
assert facade.binding() == config
assert facade.current_cutoffs() == list(limits)
template = json.loads((D / 'entry/PHYSICAL-CONFIG-REVIEW.TEMPLATE.NOT-A-PASS.json').read_bytes())
physical = load('BFD_actual_config_physical_source', template['successor_source']['path'])
assert ref(physical.__file__) == template['successor_source']
assert physical.source_chain() == template['historical_sources']
for row in template['historical_sources'].values():
    assert ref(row['path']) == row
assert template['guard_adapter'] == ref(D / 'entry/bfd_guard_facade.py')
assert len(template['historical_sources']) == 8
print(json.dumps(dict(status='PASS_EXACT_ACTUAL_BFD_FACADE_CONFIG_AND_PHYSICAL_SOURCE_BINDING_ONLY',
    source_config_refs=12, historical_source_refs=8, fixture_clocks=fixture_clocks,
    guard_calls=0, account_calls=0, observations=0, runtime_authority=None), indent=2))
