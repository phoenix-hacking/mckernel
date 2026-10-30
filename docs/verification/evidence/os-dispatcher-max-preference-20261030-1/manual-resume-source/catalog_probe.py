#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Read the local app-server's advertised model catalog without starting inference.
The catalog is not proof of entitlement, current capacity, or successful inference.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time

REPO = Path('/home/holden/mckernel')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
EFFORTS = frozenset(('low', 'medium', 'high', 'xhigh', 'max', 'ultra'))
MAX_RECORD = 1 << 20
MAX_TOTAL = 16 << 20
READ_ONLY_METHODS = frozenset(('initialize', 'model/list', 'thread/goal/get', 'thread/turns/list'))


def allowed_rpc_methods(methods):
    if (not isinstance(methods, tuple) or
            any(not isinstance(method, str) or method not in READ_ONLY_METHODS for method in methods)):
        raise ValueError('only explicit read-only catalog/goal/turn methods are allowed')
    return frozenset(methods)


def model_rows(rows):
    """Return only named GPT6 models with explicitly advertised usable efforts."""
    selected = {}
    for row in rows:
        name = row.get('model') if isinstance(row, dict) else None
        if not isinstance(name, str) or not name.startswith(('gpt-6.1-', 'gpt-6-')):
            continue
        efforts = sorted({entry.get('reasoningEffort') for entry in
                          row.get('supportedReasoningEfforts', [])
                          if isinstance(entry, dict) and entry.get('reasoningEffort') in EFFORTS})
        if efforts:
            selected[name] = {'model': name, 'efforts': efforts}
    def preference(name):
        return (0 if name == 'gpt-6.1-terra' else 1 if name.startswith('gpt-6.1-') else 2, name)
    return [selected[name] for name in sorted(selected, key=preference)]


class CatalogRPC:
    """Bounded stdio client with an explicit read-only metadata method subset."""
    def __init__(self, codex, deadline, allowed_methods=('initialize', 'model/list')):
        self.allowed_methods = allowed_rpc_methods(allowed_methods)
        self.deadline = deadline
        self.proc = subprocess.Popen([codex, '-C', str(REPO), 'app-server', '--stdio'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, start_new_session=True, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ, 'stdout')
        self.selector.register(self.proc.stderr, selectors.EVENT_READ, 'stderr')
        self.buffer = b''
        self.total = 0
        self.next_id = 0
        self.stderr_bytes = 0

    def send(self, value):
        self.proc.stdin.write((json.dumps(value, separators=(',', ':')) + '\n').encode())
        self.proc.stdin.flush()

    def call(self, method, params):
        if method not in self.allowed_methods:
            raise ValueError('explicit read-only catalog/goal/turn method required')
        self.next_id += 1
        ident = self.next_id
        self.send({'id': ident, 'method': method, 'params': params})
        while True:
            while b'\n' in self.buffer:
                raw, self.buffer = self.buffer.split(b'\n', 1)
                if len(raw) > MAX_RECORD:
                    raise ValueError('oversized catalog record')
                message = json.loads(raw)
                if message.get('id') == ident and 'method' not in message:
                    if 'error' in message:
                        error = message['error']
                        # Retain neither server error text nor configuration/authentication data.
                        raise RuntimeError('catalog RPC failed: ' + method + '; code=' + str(error.get('code')))
                    return message['result']
                if 'method' in message and 'id' in message:
                    raise RuntimeError('unexpected server request during read-only catalog probe')
            if len(self.buffer) > MAX_RECORD or self.total > MAX_TOTAL:
                raise ValueError('bounded catalog transport cap reached')
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('read-only catalog deadline reached')
            ready = self.selector.select(min(1.0, remaining))
            for key, _ in ready:
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    if key.data == 'stdout':
                        raise RuntimeError('catalog server disconnected')
                    self.selector.unregister(key.fileobj)
                    continue
                self.total += len(data)
                if key.data == 'stdout':
                    self.buffer += data
                else:
                    self.stderr_bytes += len(data)

    def close(self):
        # Only the direct owned temporary server; never inspect or signal campaign actors.
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=3)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            if self.proc.poll() is None:
                self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        finally:
            self.selector.close()
            self.proc.stdout.close()
            self.proc.stderr.close()
        if self.proc.poll() is None:
            raise RuntimeError('temporary catalog server retirement unconfirmed')


def probe(dest, timeout=30):
    """Write one immutable filtered catalog; no thread/turn/account calls occur."""
    if type(timeout) not in (int, float) or not 0 < timeout <= 45:
        raise ValueError('bounded positive catalog timeout required')
    codex = shutil.which('codex')
    if not codex:
        raise RuntimeError('codex executable unavailable')
    client = CatalogRPC(codex, time.monotonic() + timeout)
    try:
        client.call('initialize', {'clientInfo': {'name': 'mckernel-capacity-catalog', 'version': '1.0'},
                                  'capabilities': {'experimentalApi': True}})
        client.send({'method': 'initialized', 'params': {}})
        rows, cursor, seen = [], None, set()
        for _ in range(8):
            page = client.call('model/list', {'includeHidden': True, 'limit': 100, 'cursor': cursor})
            data = page.get('data')
            if not isinstance(data, list) or len(data) > 100:
                raise ValueError('invalid bounded model catalog page')
            rows.extend(data)
            cursor = page.get('nextCursor')
            if not cursor:
                break
            if not isinstance(cursor, str) or len(cursor) > 4096 or cursor in seen:
                raise ValueError('model catalog cursor invalid or repeated')
            seen.add(cursor)
        else:
            raise ValueError('model catalog pagination cap reached')
        models = model_rows(rows)
        if not models:
            raise ValueError('no eligible GPT6 model/effort pairs advertised')
    finally:
        client.close()
    record = dict(scope=SCOPE, observed_at=datetime.now(timezone.utc).isoformat(),
                  source='local Codex app-server model/list', models=models,
                  inference_started=False, catalog_only_not_entitlement_or_capacity_proof=True,
                  temporary_server_pid=client.proc.pid, temporary_server_returncode=client.proc.returncode,
                  temporary_server_retired=True, stderr_bytes_discarded=client.stderr_bytes,
                  documentation='https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server')
    path = Path(dest)
    with path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    return record


def self_test():
    rows = [{'model': name, 'supportedReasoningEfforts': [{'reasoningEffort': 'high'},
                                                        {'reasoningEffort': 'medium'}]}
            for name in ('gpt-5.6', 'gpt-6-sol', 'gpt-6.1-sol', 'gpt-6.1-terra')]
    assert [r['model'] for r in model_rows(rows)] == ['gpt-6.1-terra', 'gpt-6.1-sol', 'gpt-6-sol']
    assert model_rows([{'model': 'gpt-6.1-terra', 'supportedReasoningEfforts': []}]) == []
    assert model_rows([{}, None, {'model': 6}, {'model': 'gpt-6.1-terra',
                       'supportedReasoningEfforts': [{'reasoningEffort': 'unknown'}]}]) == []
    assert model_rows(rows + rows) == model_rows(rows)
    assert allowed_rpc_methods(('initialize', 'thread/goal/get', 'thread/turns/list')) <= READ_ONLY_METHODS
    try:
        allowed_rpc_methods(('initialize', 'turn/start'))
    except ValueError:
        pass
    else:
        raise AssertionError('mutating method must be rejected before process creation')
    return {'pure_filter_checks': 4, 'pure_read_only_whitelist_checks': 2,
            'status': 'PASS', 'inference_started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test()))
    elif args.output:
        value = probe(args.output)
        print(json.dumps({'models': value['models'], 'temporary_server_retired': True,
                          'inference_started': False}))
    else:
        parser.error('supply --output or --self-test')
