"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit source successor retaining historical physical predicates and provenance.
No runtime binding, guard invocation or physical observation occurs on import.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.abc
import importlib.util
import json
import subprocess
import types

HERE = Path(__file__).resolve().parent
E = HERE.parent
ROOT = E / 'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/attempt4-root51-boundary-contract-correction-source-1/observe_root51_current115_attempt4.py'
ROOT_SHA = 'b3abfdada1909b9b3a945f522cb0f6b7abe0dc87b7bba5e844ee4d1703b127ad'
OLD_GUARD = E / 'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'
OLD_GUARD_SHA = '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
_BINDING = None


def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def authenticated(row):
    assert set(row) == {'path', 'bytes', 'sha256'} and ref(row['path']) == row
    return Path(row['path'])


def source_chain():
    """Discover only literal historical observer dependencies, authenticating every edge."""
    assert ref(ROOT)['sha256'] == ROOT_SHA
    found = {}
    pending = [ROOT]
    while pending:
        path = pending.pop()
        if str(path) in found:
            continue
        tree = ast.parse(path.read_bytes())
        found[str(path)] = ref(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            try:
                value = ast.literal_eval(node)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, dict) or set(value) != {'path', 'bytes', 'sha256'}:
                continue
            target = Path(value['path'])
            if target.suffix == '.py' and (target.name.startswith('observe_') or target.name == 'check_postnative_current_new12h.py'):
                authenticated(value)
                pending.append(target)
    return found


def configure(binding_ref):
    global _BINDING
    assert _BINDING is None, 'one immutable runtime binding'
    binding = json.loads(authenticated(binding_ref).read_bytes())
    assert binding['author'] == '/root' and binding['successor_source'] == ref(__file__)
    assert binding['historical_sources'] == source_chain()
    review = json.loads(authenticated(binding['independent_review']).read_bytes())
    assert review['independent'] is True and review['implementation_ownership'] is False
    assert review['decision'] == 'PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR'
    assert review['successor_source'] == ref(__file__)
    assert review['historical_sources'] == binding['historical_sources']
    assert review['guard_adapter'] == binding['guard_adapter'] and review['guard_config'] == binding['guard_config']
    authenticated(binding['guard_adapter']); authenticated(binding['guard_config'])
    _BINDING = (binding_ref, binding)


def binding():
    assert _BINDING is not None, 'Root exact reviewed runtime dependency binding required'
    row, value = _BINDING
    assert json.loads(authenticated(row).read_bytes()) == value
    return value


def guard_module():
    value = binding()
    path = authenticated(value['guard_adapter'])
    spec = importlib.util.spec_from_file_location('explicit_new_window_physical_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure(value['guard_config'])
    return module


class SuccessorTransform(ast.NodeTransformer):
    """Only dependency routing, guard selection and historical provenance expressions."""
    def __init__(self, historical_path, guard_ref):
        self.path = str(historical_path)
        self.guard_ref = guard_ref
        self.changes = []

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id == '__file__':
            self.changes.append('historical source provenance expression')
            return ast.copy_location(ast.Constant(self.path), node)
        return node

    def visit_Assign(self, node):
        if any(isinstance(t, ast.Name) and t.id in ('GUARD', 'GUARD_SHA') for t in node.targets):
            name = node.targets[0].id
            self.changes.append(name + ' selects actual reviewed adapter identity')
            expression = 'Path(' + repr(self.guard_ref['path']) + ')' if name == 'GUARD' else repr(self.guard_ref['sha256'])
            return ast.copy_location(ast.Assign(targets=node.targets, value=ast.parse(expression, mode='eval').body), node)
        return self.generic_visit(node)

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if ast.unparse(node.func) == 'importlib.util.spec_from_file_location':
            self.changes.append('authenticated dependency import routing')
            node.func = ast.Name(id='_successor_spec', ctx=ast.Load())
        elif ast.unparse(node.func) == 'subprocess.run':
            self.changes.append('observer child routing; Docker argv unchanged')
            node.func = ast.Name(id='_successor_run', ctx=ast.Load())
        return node

    def visit_FunctionDef(self, node):
        if node.name == 'current_window_guard':
            self.changes.append('inline expired guard loader delegates authenticated operation adapter')
            node.body = ast.parse('return _successor_guard().guard()').body
            return node
        return self.generic_visit(node)


def transformed(path, guard_ref):
    transform = SuccessorTransform(path, guard_ref)
    tree = transform.visit(ast.parse(Path(path).read_bytes()))
    ast.fix_missing_locations(tree)
    return tree, transform.changes


class HistoricalSuccessorLoader(importlib.abc.Loader):
    def __init__(self, path):
        self.path = Path(path)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        value = binding()
        authenticated(value['historical_sources'][str(self.path)])
        tree, _ = transformed(self.path, value['guard_adapter'])
        # Metadata names the actual successor. Historical source expressions above
        # remain explicit historical provenance and never claim transformed bytes match.
        module.__file__ = str(Path(__file__).resolve())
        module.__dict__.update(_successor_spec=successor_spec, _successor_run=successor_run,
                               _successor_guard=guard_module)
        exec(compile(tree, str(self.path) + ':EXPLICIT_NEW_WINDOW_SUCCESSOR', 'exec'), module.__dict__)


def successor_spec(name, location, *args, **kwargs):
    path = str(Path(location))
    value = binding()
    if path == str(OLD_GUARD) or path == value['guard_adapter']['path']:
        # Real adapter metadata keeps its own actual file/origin. Configure once.
        adapter = guard_module()
        class GuardLoader(importlib.abc.Loader):
            def create_module(self, spec):
                return adapter
            def exec_module(self, module):
                return None
        return importlib.util.spec_from_loader(name, GuardLoader(), origin=adapter.__file__)
    if path in value['historical_sources']:
        return importlib.util.spec_from_loader(name, HistoricalSuccessorLoader(path), origin=str(Path(__file__).resolve()))
    raise ValueError('undeclared dependency import: ' + path)


def successor_run(argv, *args, **kwargs):
    value = binding()
    rewritten = list(argv)
    for index, item in enumerate(rewritten):
        if item in value['historical_sources']:
            # Same interpreter/profile and subprocess timeout; selected observer only.
            rewritten[index:index + 1] = [str(Path(__file__).resolve()), '--historical', item,
                                          '--runtime-binding', _BINDING[0]['path'],
                                          '--runtime-binding-sha256', _BINDING[0]['sha256']]
            break
    return subprocess.run(rewritten, *args, **kwargs)


def observe(historical=ROOT):
    value = binding()
    assert str(historical) in value['historical_sources']
    spec = successor_spec('exact_physical_history_successor', historical)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.observe()
    result['explicit_new_window_physical_successor'] = ref(__file__)
    result['historical_predicate_source'] = value['historical_sources'][str(historical)]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--check-source-chain', action='store_true')
    parser.add_argument('--historical', type=Path, default=ROOT)
    parser.add_argument('--runtime-binding', type=Path)
    parser.add_argument('--runtime-binding-sha256')
    args = parser.parse_args()
    if args.check_source_chain:
        print(json.dumps(dict(status='PASS_EXACT_PHYSICAL_HISTORY_SOURCE_CHAIN_ONLY', sources=source_chain(), runtime_authority=None, observations=0, guard_calls=0), indent=2))
        return
    assert args.runtime_binding and ref(args.runtime_binding)['sha256'] == args.runtime_binding_sha256
    configure(ref(args.runtime_binding))
    print(json.dumps(observe(args.historical), indent=2))


if __name__ == '__main__':
    main()
