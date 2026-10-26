"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Execute only AST-extracted collector/validator against an in-memory proc model.
No source module import, real proc reads, root command, or workload execution.
"""
import ast
import builtins
import copy
import errno
import io
import json
import os
from pathlib import Path
import sys
import types


def stat(pid, start=None, state=b'S'):
    fields = [state] + [b'0'] * 49
    fields[1] = b'1'
    fields[19] = str(pid * 10 if start is None else start).encode()
    return str(pid).encode() + b' (fixture) ' + b' '.join(fields) + b'\n'


class Model:
    def __init__(self, entries=None, hook=None):
        self.entries = entries or [[1, 20, 31]] * 6
        self.hook = hook or (lambda *args: None)
        self.snapshot = 0
        self.counts = {}
        self.prints = []

    def event(self, op, path):
        key = (self.snapshot, op, path)
        self.counts[key] = self.counts.get(key, 0) + 1
        replacement = self.hook(self, op, path, self.counts[key])
        if isinstance(replacement, BaseException):
            raise replacement
        return replacement

    def listdir(self, path):
        self.event('listdir', path)
        self.snapshot += 1
        return list(map(str, self.entries[self.snapshot - 1]))

    def open(self, path, mode='r'):
        replacement = self.event('open', path)
        if replacement is not None:
            data = replacement
        elif path == '/proc/sys/kernel/random/boot_id':
            data = 'fixture-boot\n'
        elif path.endswith('/stat'):
            data = stat(int(path.split('/')[2]))
        elif path.endswith('/cmdline'):
            data = b'/bin/sh\0'
        else:
            raise AssertionError(('unexpected-open', path))
        return io.BytesIO(data) if 'b' in mode else io.StringIO(data)

    def readlink(self, path):
        return self.event('readlink', path) or '/bin/sh'

    def execute(self, code):
        fake_os = types.SimpleNamespace(path=os.path, listdir=self.listdir,
                                        readlink=self.readlink, geteuid=lambda: 0)
        fake_sys = types.SimpleNamespace(argv=['collector', 'challenge', '20', '200'])
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            return {'os': fake_os, 'sys': fake_sys}.get(name) or original_import(name, *args, **kwargs)

        scope = {'__builtins__': dict(vars(builtins), open=self.open,
                 __import__=fake_import, print=lambda value: self.prints.append(value))}
        exec(compile(code, '<independent-memory-proc>', 'exec'), scope)
        assert len(self.prints) == 1
        return json.loads(self.prints[0])


def expect_failure(code, model, kind, text):
    try:
        model.execute(code)
    except kind as error:
        assert text in str(error), str(error)
    else:
        raise AssertionError('expected refusal')
    assert not model.prints


def main():
    source = Path(sys.argv[1])
    tree = ast.parse(source.read_text())
    code = next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROC_CODE' for t in node.targets))
    checks = []
    report = Model().execute(code)
    assert report['attempts'] == 1 and report['retry_failures'] == []
    checks.append('stable complete pair')

    def failed_second(model, op, path, count):
        if model.snapshot == 2 and path == '/proc/32/stat':
            return FileNotFoundError(errno.ENOENT, 'ordinary exit', path)
    model = Model([[1, 20, 31], [1, 20, 32], [1, 20, 33], [1, 20, 34]], failed_second)
    retried = model.execute(code)
    assert model.snapshot == 4 and retried['attempts'] == 2
    assert [row[0] for row in retried['snapshots'][0]] == [1, 20, 33]
    assert [row[0] for row in retried['snapshots'][1]] == [1, 20, 34]
    assert retried['retry_failures'][0]['snapshot'] == 2
    checks.append('failed second snapshot discards entire pair')

    def wrong_path(model, op, path, count):
        if path == '/proc/31/stat':
            return FileNotFoundError(errno.ENOENT, 'unknown path', '/unexpected')
    model = Model(hook=wrong_path)
    expect_failure(code, model, FileNotFoundError, '/unexpected')
    assert model.snapshot == 1
    checks.append('foreign filename ENOENT is immediate refusal')

    def enumerate_missing(model, op, path, count):
        if op == 'listdir':
            return FileNotFoundError(errno.ENOENT, 'unknown enumeration', path)
    model = Model(hook=enumerate_missing)
    expect_failure(code, model, FileNotFoundError, '/proc')
    assert model.snapshot == 0
    checks.append('enumeration ENOENT is immediate refusal')

    def publisher_last_stat(model, op, path, count):
        if op == 'readlink' and path == '/proc/31/exe':
            return '/usr/bin/gcc'
        if path == '/proc/31/stat' and count == 2:
            return FileNotFoundError(errno.ENOENT, 'publisher exit', path)
    model = Model(hook=publisher_last_stat)
    expect_failure(code, model, ValueError, 'publisher')
    assert model.snapshot == 1
    checks.append('known executable publisher final-stat exit is hard refusal')

    def malformed_protected(model, op, path, count):
        if model.snapshot == 0 and path == '/proc/20/stat' and count == 2:
            return stat(20, state=b'Q')
    model = Model(hook=malformed_protected)
    expect_failure(code, model, ValueError, 'caller')
    assert model.snapshot == 0
    checks.append('malformed intermediate protected caller state is hard refusal')

    def reused(model, op, path, count):
        if path == '/proc/31/stat' and count == 2:
            return stat(31, start=999)
    model = Model(hook=reused)
    expect_failure(code, model, ValueError, 'process-raced')
    assert model.snapshot == 1
    checks.append('noncaller changed birth is hard refusal')

    validator = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_process_report')
    class Refusal(Exception):
        pass
    scope = {'Refusal': Refusal, 'BOOT_ID': 'fixture-boot', 'OWNER_PID': 900, 'WAITER_PIDS': []}
    exec(compile(ast.Module(body=[validator], type_ignores=[]), '<independent-validator>', 'exec'), scope)
    validate = scope['validate_process_report']
    validate(retried, 'challenge', [20, '200'])
    checks.append('real validator accepts authentic bounded retry report')
    for key, value in [('attempts', True), ('attempts', 4), ('retry_failures', [])]:
        invalid = copy.deepcopy(retried)
        invalid[key] = value
        try:
            validate(invalid, 'challenge', [20, '200'])
        except Refusal:
            pass
        else:
            raise AssertionError(('invalid-metadata-accepted', key, value))
    checks.append('validator rejects bool/excess attempts and omitted retry metadata')
    print(json.dumps({'scope': __doc__.splitlines()[0], 'decision': 'PASS', 'checks': checks}, sort_keys=True))


if __name__ == '__main__':
    main()
