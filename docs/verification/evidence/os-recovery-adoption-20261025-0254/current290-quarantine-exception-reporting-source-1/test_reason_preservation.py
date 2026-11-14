"""Functional OS harness evidence regression only; no security testing."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parent
inputs = json.loads((root / 'INPUTS.json').read_text())


class Refusal(RuntimeError):
    pass


class FixtureStop(BaseException):
    pass


def exercise(path, message):
    records = []
    events = []
    class Transaction:
        fd = 1
        root_locked = True
        mutation_started = True
        def run(self, execute):
            assert execute is True
            raise Refusal(message)
        def create(self, name, raw):
            assert name == 'fixture-only.json'
            records.append(json.loads(raw))
        def close(self):
            events.append('closed')
    def stop():
        raise FixtureStop()
    namespace = dict(signal=SimpleNamespace(SIG_BLOCK=0, SIG_SETMASK=1,
        pthread_sigmask=lambda *_: 'fixture-mask'), DEFERRED_SIGNALS=set(),
        Transaction=Transaction, QUARANTINE=Path('fixture-only.json'),
        RELEASE={'fixture': True}, digest=lambda raw: hashlib.sha256(raw).hexdigest(),
        canonical=lambda value: json.dumps(value, sort_keys=True).encode(),
        json=json, DEAD_CALLER_OBSERVATIONS=[], quarantine_wait=stop)
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'recover')
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            namespace['recover'](True)
    except FixtureStop:
        pass
    else:
        raise AssertionError('fixture did not reach retained quarantine branch')
    assert events == ['closed'] and len(records) == 1
    return records[0], json.loads(stdout.getvalue())


for message in ('functional census fixture A', 'functional census fixture B: exact cause'):
    original = exercise(Path(inputs['original']), message)
    corrected = exercise(Path(inputs['corrected']), message)
    assert all('error_message' not in row for row in original)
    assert all(row['error_message'] == message for row in corrected)
    assert all(row['error_type'] == 'Refusal' for row in corrected)
    for before, after in zip(original, corrected):
        assert before == {key: value for key, value in after.items() if key != 'error_message'}
print('PASS: distinct exact reasons retained in durable and stdout fixtures; all other fields unchanged; no live operations')
