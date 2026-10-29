"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicitly configured no-argument adapter; no live checks occur during configuration.
The Root caller pins this source AND the separate immutable config byte reference.
No config path/hash is embedded here, avoiding adapter/successor hash cycles.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
OPERATION = 'current119-postjoin-current67'
_bound = None


def need(ok, why):
    if not ok:
        raise ValueError(why)


def raw_reference(ref):
    need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'}, 'exact config/source byte reference')
    path = Path(ref['path'])
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'absolute regular config/source')
    raw = path.read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'sealed config/source bytes')
    return raw


def configure(config_ref):
    """Caller must authenticate config_ref in its independently reviewed source closure."""
    global _bound
    need(_bound is None, 'operation adapter config is one-time immutable')
    raw = raw_reference(config_ref)
    # Source config is declared JSON. Shared module subsequently enforces strict JSON.
    initial = json.loads(raw)
    source = initial['shared_guard']
    raw_reference(source)
    spec = importlib.util.spec_from_file_location('operation_guard_for_' + OPERATION, source['path'])
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    config = shared.decode(raw)
    need(set(config) == {'schema', 'operation', 'shared_guard', 'successor', 'review', 'subjects'}, 'exact adapter config keys')
    need(config['schema'] == 'mckernel.sealed-operation-guard-adapter-config.v1'
         and config['operation'] == OPERATION, 'exact per-operation adapter config')
    successor = shared.authenticated(config['successor'], declared_json=True)
    review = shared.authenticated(config['review'], declared_json=True)
    shared.validate_operation(successor, review, OPERATION, config['subjects'], [0, 0, 0], BOOT)
    _bound = (config_ref.copy(), config, shared)


def binding():
    need(_bound is not None, 'explicit sealed operation config required; no window-only default')
    config_ref, config, shared = _bound
    need(shared.decode(raw_reference(config_ref)) == config, 'immutable operation config')
    raw_reference(config['shared_guard'])
    return config, shared


def current_cutoffs():
    config, shared = binding()
    successor = shared.authenticated(config['successor'], declared_json=True)
    review = shared.authenticated(config['review'], declared_json=True)
    return shared.validate_operation(successor, review, OPERATION, config['subjects'], [0, 0, 0], BOOT)


def guard():
    config, shared = binding()
    return shared.guard(OPERATION, config['successor'], config['review'], config['subjects'])
