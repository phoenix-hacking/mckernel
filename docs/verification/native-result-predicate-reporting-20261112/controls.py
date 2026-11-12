"""Focused reporting controls extending the existing qualified runner only.

No validator, issuer, account, Root actor, real signal/wait, or native call runs.
Source pins and separate actual Root review/admission are mandatory before use.
"""
import ast
import builtins
import errno
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
CASE_NAMES = ('fresh_controls_valueerror', 'installed_proof_valueerror',
              'proof_cap_valueerror', 'ack_valueerror',
              'report_failure_secondary_same_custody',
              'success_ack_wait_source_equivalence')


def need(value, message):
    if not value:
        raise AssertionError(message)


def read_source(ref):
    raw = pathlib.Path(ref['path']).read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
         'exact focused-control input changed')
    return raw


def existing_runner(ref):
    raw = read_source(ref)
    module = types.ModuleType('_qualified_reporting_runner_definitions')
    module.__file__ = ref['path']
    # Only its already-qualified definitions are loaded. __name__ is not main.
    exec(compile(raw, ref['path'], 'exec'), module.__dict__)
    return module


def module(name, **values):
    result = types.ModuleType(name)
    result.__dict__.update(values)
    return result


def environment(base, pins, failure_mode=None):
    """Reuse Registry/ControlledOS; declare only borrowed stderr extensions."""
    class ReportIO(base.ControlledOS):
        def __init__(self):
            super().__init__()
            self.O_ACCMODE = os.O_ACCMODE
            self.failure = OSError(errno.EIO, 'private controlled report I/O')
            self.public_events = []

        def fstat(self, fd):
            need(fd == 2, 'only borrowed stderr metadata may be observed')
            self.public_events.append(('fstat', fd))
            return types.SimpleNamespace(st_mode=stat.S_IFREG | 0o600,
                                         st_uid=1000, st_nlink=1)

        def write(self, fd, raw):
            need(fd == 2 and type(raw) is bytes, 'only borrowed stderr DATA write')
            self.public_events.append(('write', fd))
            if failure_mode == 'write':
                raise self.failure
            self.buffers[fd] += raw
            return len(raw)

        def fsync(self, fd):
            need(fd == 2, 'only borrowed stderr fsync')
            self.public_events.append(('fsync', fd))
            if failure_mode == 'fsync':
                raise self.failure

        def close(self, fd):
            raise AssertionError('reporter cannot close a borrowed handle')

        def waitpid(self, *args):
            raise AssertionError('focused reporting cannot perform any wait')

    io = ReportIO()
    def fcntl(fd, command):
        need(fd == 2 and command == 3, 'borrowed stderr F_GETFL only')
        return os.O_WRONLY
    mapping = {
        'os': io, 'json': json,
        'fcntl': module('fcntl', fcntl=fcntl, F_GETFL=3),
        'signal': module('signal'), 'select': module('select'),
        'socket': module('socket'), 'time': module('time'),
        'deferred_fork': module('deferred_fork'),
        'direct_entry': module('direct_entry'),
        'parent_control': module('parent_control'),
        'pidfd_compat': module('pidfd_compat'),
        'caller_data_output': module('caller_data_output'),
    }
    for name in ('ownership_latch', 'direct_completion', 'root_parent'):
        mapping[name] = module(name, __file__=pins[name]['path'])
    allowed = set(mapping) | {'hashlib', 'stat', 'contextlib', 'threading', 'sys'}
    def no_open(*args, **kwargs):
        raise AssertionError('SUT has no real filesystem authority')
    def imported(name, globals=None, locals=None, fromlist=(), level=0):
        need(level == 0 and name in allowed, 'only declared inert/stdlib import')
        return builtins.__import__(name, globals, locals, fromlist, level)
    return io, mapping, imported, no_open


class BoundModules:
    def __init__(self, base, pins, failure_mode=None):
        self.base, self.pins = base, pins
        self.io, self.mapping, self.imported, self.no_open = environment(base, pins, failure_mode)

    def __enter__(self):
        self.registry = self.base.Registry(self.mapping)
        self.registry.__enter__()
        try:
            for name in ('ownership_latch', 'direct_completion', 'root_parent'):
                target = self.mapping[name]
                target.__dict__['__builtins__'] = dict(vars(builtins), open=self.no_open,
                                                      __import__=self.imported)
                exec(compile(read_source(self.pins[name]), target.__file__, 'exec'), target.__dict__)
            self.parent = self.mapping['root_parent']
            self.completion = self.mapping['direct_completion']
            self.latch = self.mapping['ownership_latch'].CustodyLatch('PARENT_OWNED')
            self.handles = [object(), object(), object()]
            self.latch.retain(*self.handles)
            for name in ('_retain_result_verify_primary', '_result_verify_reporting_secondary',
                         '_result_verify_reported_stage', '_failure_note'):
                fn = getattr(self.parent, name)
                need(fn.__globals__ is self.parent.__dict__ and fn.__code__.co_filename == self.parent.__file__,
                     'actual full parent function/global binding')
            need(self.parent.direct_completion is self.completion and self.parent.os is self.io,
                 'actual complete imported module identity')
            return self
        except BaseException:
            self.registry.__exit__(None, None, None)
            raise

    def __exit__(self, *unused):
        self.registry.__exit__(*unused)

    def same_custody(self):
        need(self.latch.state == 'PARENT_OWNED' and self.latch.retained == self.handles and
             not self.latch.children and self.latch.failure is None,
             'reporting leaves the exact same custody and state')
        need(not self.io.wait_calls and not self.io.rows and self.io.buffers[1] == b'',
             'no descriptor/process/extra-stream effect')


def emit_case(base, pins, tag, origin, failure_mode=None):
    with BoundModules(base, pins, failure_mode) as h:
        h.completion.RESULT_VERIFY_SUBSTAGE = tag if origin == 'result_verify' else 'result_installed_proof'
        primary = ValueError('PRIVATE ORIGINAL RESULT FAILURE ' + tag)
        try:
            raise primary
        except ValueError:
            tb = primary.__traceback__
            original_args = primary.args
            h.parent._retain_result_verify_primary(primary)
            reported = h.parent._result_verify_reported_stage(origin)
            need(reported == tag, 'closed correct source span; stale hint cannot override parent span')
            done = h.parent._failure_note('root_parent', reported, primary,
                                         {'pid':4242, 'birth':'333'}, {'pid':5151, 'birth':'444'})
        need(h.parent._RESULT_VERIFY_RAW_PRIMARY == (primary, tb) and
             h.parent._RESULT_VERIFY_RAW_PRIMARY[0] is primary and primary.args is original_args,
             'original object/args/TB retained privately without replacement')
        # First-only private primary remains authoritative on a later report error.
        h.parent._retain_result_verify_primary(ValueError('SECONDARY MUST NOT REPLACE PRIMARY'))
        need(h.parent._RESULT_VERIFY_RAW_PRIMARY[0] is primary, 'private primary is first-only')
        h.same_custody()
        if failure_mode:
            need(done is False and any(row[0] is h.io.failure for row in h.parent._RESULT_VERIFY_RAW_SECONDARY),
                 'exact actual lower report failure retained as secondary only')
            return
        need(done is True and not h.parent._RESULT_VERIFY_RAW_SECONDARY,
             'complete fixed reporting with no unexpected global/error')
        record = json.loads(h.io.buffers[2])
        expected_keys = {'record_type','scope','role','stage','error_class','error_message',
                         'message_policy','errno','root_parent','keeper','authority',
                         'native_release','native_currentfree','outcome'}
        need(set(record) == expected_keys and record['record_type'] == 'ROOT_INSTALL_FAILURE_DATA_V1',
             'same DATA_V1 schema/keyset')
        need(record['stage'] == tag and record['error_class'] == 'ValueError' and
             record['error_message'] == 'fixed source reporting span: ' + tag and
             record['message_policy'] == 'exact_fixed' and record['errno'] is None,
             'only fixed source identifier, original class retained')
        need(primary.args[0].encode() not in h.io.buffers[2] and record['authority'] is None and
             record['native_release'] is False and record['native_currentfree'] is None and
             record['outcome'] == 'UNKNOWN', 'no raw private values or authority released')


class StripDiagnostics(ast.NodeTransformer):
    def __init__(self, tags):
        self.tags = set(tags)

    def visit_Assign(self, node):
        names = {x.id for x in node.targets if isinstance(x, ast.Name)}
        if 'RESULT_VERIFY_SUBSTAGE' in names:
            return None
        if names == {'stage'} and isinstance(node.value, ast.Constant) and node.value.value in self.tags:
            return None
        return self.generic_visit(node)

    def visit_Global(self, node):
        return None if node.names == ['RESULT_VERIFY_SUBSTAGE'] else node

    def visit_Expr(self, node):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == '_retain_result_verify_primary':
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        node = self.generic_visit(node)
        return None if not node.body and not node.orelse else node

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == '_result_verify_reported_stage':
            need(len(node.args) == 1, 'fixed reporting-stage selection only')
            return self.visit(node.args[0])
        return self.generic_visit(node)


def source_equivalence(pins):
    tags = ('result_sealed_context','result_fresh_controls','result_post_controls',
            'result_fields','result_installed_proof','result_proof_compare',
            'result_keeper_journal','result_captures','result_durable','result_proof_cap','result_ack')
    for proposed, baseline, names in (
        ('root_parent','baseline_parent',('run',)),
        ('direct_completion','baseline_completion',('_parent_context','verify_parent_result'))):
        old = ast.parse(read_source(pins[baseline]))
        new = ast.parse(read_source(pins[proposed]))
        for name in names:
            before = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)
            after = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == name)
            after = StripDiagnostics(tags).visit(after)
            need(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False),
                 'all original guards/returns/ACK/wait/caps/custody paths preserved: ' + name)
    completion_tree = ast.parse(read_source(pins['direct_completion']))
    parent_tree = ast.parse(read_source(pins['root_parent']))
    def function(tree, name):
        return next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name)
    def marker(fn, name, tag):
        return next(x for x in ast.walk(fn) if isinstance(x, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == name for t in x.targets) and
            isinstance(x.value, ast.Constant) and x.value.value == tag)
    context = function(completion_tree, '_parent_context')
    fresh = next(x for x in ast.walk(context) if isinstance(x, ast.Call) and
        isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) and
        x.func.value.id == 'issuer' and x.func.attr == 'fresh_controls')
    need(marker(context, 'RESULT_VERIFY_SUBSTAGE', 'result_fresh_controls').lineno < fresh.lineno <
         marker(context, 'RESULT_VERIFY_SUBSTAGE', 'result_post_controls').lineno,
         'actual fresh_controls source call is bracketed by fixed memory spans')
    result = function(completion_tree, 'verify_parent_result')
    proof = next(x for x in ast.walk(result) if isinstance(x, ast.Call) and
        isinstance(x.func, ast.Name) and x.func.id == 'install_proof')
    need(marker(result, 'RESULT_VERIFY_SUBSTAGE', 'result_installed_proof').lineno < proof.lineno <
         marker(result, 'RESULT_VERIFY_SUBSTAGE', 'result_proof_compare').lineno,
         'actual installed-proof call has the precise reporting span')
    run = function(parent_tree, 'run')
    cap = next(x for x in ast.walk(run) if isinstance(x, ast.If) and
        any(isinstance(y, ast.Constant) and y.value == 'proof verification cap' for y in ast.walk(x)))
    ack = next(x for x in ast.walk(run) if isinstance(x, ast.Call) and
        isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) and
        x.func.value.id == 'ipc' and x.func.attr == 'send' and
        any(isinstance(y, ast.Constant) and y.value == 'RESULT_ACK' for y in ast.walk(x)))
    need(marker(run, 'stage', 'result_proof_cap').lineno < cap.lineno <
         marker(run, 'stage', 'result_ack').lineno < ack.lineno,
         'original cap/ACK order with distinct fixed source spans')


def main():
    pins = json.loads((HERE/'SOURCE-PINS.json').read_bytes())
    base = existing_runner(pins['existing_runner'])
    cases = []
    specs = ((CASE_NAMES[0], 'result_fresh_controls', 'result_verify'),
             (CASE_NAMES[1], 'result_installed_proof', 'result_verify'),
             (CASE_NAMES[2], 'result_proof_cap', 'result_proof_cap'),
             (CASE_NAMES[3], 'result_ack', 'result_ack'))
    for name, tag, origin in specs:
        emit_case(base, pins, tag, origin)
        cases.append({'name':name, 'pass':True})
    for mode in ('write','fsync'):
        emit_case(base, pins, 'result_fresh_controls', 'result_verify', mode)
    cases.append({'name':CASE_NAMES[4], 'pass':True})
    source_equivalence(pins)
    cases.append({'name':CASE_NAMES[5], 'pass':True})
    print(json.dumps({'status':'PASS_FOCUSED_FIXED_RESULT_REPORTING_ONLY', 'cases':cases,
        'original_control_guards_ACK_wait_custody_preserved':True,
        'actual_verifier_issuer_account_native_execution':False}, sort_keys=True, separators=(',',':')))


if __name__ == '__main__':
    main()
