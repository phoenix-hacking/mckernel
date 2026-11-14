"""Fixture-only transaction/signal regressions: never invokes sudo or Docker."""
import importlib.util
import json
import os
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).parents[2] / 'docs/verification/evidence/native-exact-export26-build-cleanup-20261001.py'
spec = importlib.util.spec_from_file_location('export26_cleanup', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REAL_QUARANTINE = m.quarantine_exclusion


def test_attempt_four_bindings_consume_fresh_paths_and_reject_prior_attempts():
    assert m.RELEASE_PATH.endswith('-4.json')
    assert m.EVIDENCE.name.endswith('-4')
    assert m.QUARANTINE.endswith('-4-quarantine')
    for old in ('-20261001-1', '-20261001-2', '-20261001-3'):
        assert old not in m.RELEASE_PATH
        assert old not in str(m.EVIDENCE)
        assert old not in m.QUARANTINE


def result(data=b'', code=0, err=b''):
    return SimpleNamespace(returncode=code, stdout=data, stderr=err)


def rows(target=False):
    values = [{'ID': m.OLD_CONTAINER, 'Names': m.OLD_NAME, 'State': 'exited'}]
    if target:
        values.append({'ID': m.CONTAINER, 'Names': m.NAME, 'State': 'exited'})
    return result(b'\n'.join(json.dumps(x).encode() for x in values))


@pytest.fixture(autouse=True)
def no_commands(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('unmocked external command')
    monkeypatch.setattr(m.subprocess, 'run', reject)


@pytest.fixture
def transaction(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'EVIDENCE', tmp_path / 'one-shot')
    monkeypatch.setattr(m, 'release_guard', lambda *a: b'release')
    monkeypatch.setattr(m, 'retired', lambda: None)
    monkeypatch.setattr(m, 'exclusion', lambda *a: b'exclusion')
    monkeypatch.setattr(m, 'snapshot', lambda: {'protected': 'unchanged'})
    monkeypatch.setattr(m, 'inspect', lambda *a: {})
    monkeypatch.setattr(m, 'checked', lambda *a: (b'log', None))
    monkeypatch.setattr(m, 'LOG_SHA', m.sha(b'log'))
    monkeypatch.setattr(m, 'absent', lambda *a: None)
    calls = []

    def docker(*args):
        calls.append(args)
        if args[0] == 'ps':
            return rows(target=not any(c[0] == 'rm' for c in calls))
        if args[0] == 'inspect':
            return result(b'[]')
        if args[0] == 'logs':
            return result(b'log')
        if args == ('rm', m.CONTAINER):
            return result(m.CONTAINER.encode() + b'\n')
        raise AssertionError(args)

    monkeypatch.setattr(m, 'docker', docker)
    monkeypatch.setattr(m, 'quarantine_exclusion', lambda *a: calls.append(('quarantine',)))
    return calls, docker


def test_success_order_and_durable_capture(transaction):
    calls, docker = transaction
    m.execute('a' * 40, 'b' * 64)
    assert [x[0] for x in calls] == ['ps', 'inspect', 'logs', 'rm', 'ps', 'quarantine']
    assert (m.EVIDENCE / 'PASS.json').is_file()
    assert (m.EVIDENCE / 'inspect-before.stdout').read_bytes() == b'[]'
    assert (m.EVIDENCE / 'retained-container.log').read_bytes() == b'log'
    assert (m.EVIDENCE / 'absence-proven.json').is_file()


def test_second_invocation_never_reaches_daemon(transaction):
    calls, _ = transaction
    m.execute('a' * 40, 'b' * 64)
    before = list(calls)
    with pytest.raises(FileExistsError):
        m.execute('a' * 40, 'b' * 64)
    assert calls == before


@pytest.mark.parametrize('code,data,err', [(1, b'', b''), (0, b'', b''),
    (0, b'[]', b''), (0, b'not json', b''), (0, b'{}', b''),
    (0, b'{}', b'permission denied'), (2, b'valid-looking', b'')])
def test_absence_requires_successful_nonempty_full_census(code, data, err):
    with pytest.raises((m.Error, TypeError, AttributeError)):
        m.census(result(data, code, err))


@pytest.mark.parametrize('change', ['prefix', 'duplicate', 'old_missing', 'old_running', 'old_renamed'])
def test_census_requires_exact_export25_preservation(change):
    r = json.loads(rows().stdout)
    values = [r]
    if change == 'prefix':
        r['ID'] = r['ID'][:12]
    elif change == 'duplicate':
        values.append(dict(r))
    elif change == 'old_missing':
        r['ID'] = 'f' * 64
    elif change == 'old_running':
        r['State'] = 'running'
    else:
        r['Names'] = 'changed'
    with pytest.raises(m.Error):
        m.census(result(b'\n'.join(json.dumps(x).encode() for x in values)))


@pytest.mark.parametrize('failure', ['rm_error', 'rm_empty', 'rm_stderr', 'post_error',
                                   'post_empty', 'post_present', 'post_invalid', 'post_timeout'])
def test_uncertain_removal_preserves_exclusion(transaction, monkeypatch, failure):
    calls, real = transaction

    def docker(*args):
        answer = real(*args)
        if args[0] == 'rm' and failure.startswith('rm_'):
            return {'rm_error': result(code=1), 'rm_empty': result(),
                    'rm_stderr': result(m.CONTAINER.encode(), err=b'error')}[failure]
        if args[0] == 'ps' and any(c[0] == 'rm' for c in calls):
            if failure == 'post_timeout':
                raise TimeoutError('daemon observation timed out')
            return {'post_error': result(code=1), 'post_empty': result(),
                    'post_present': rows(True), 'post_invalid': result(b'???')}.get(failure, answer)
        return answer

    monkeypatch.setattr(m, 'docker', docker)
    with pytest.raises((m.Error, TimeoutError)):
        m.execute('a' * 40, 'b' * 64)
    assert ('quarantine',) not in calls
    assert (m.EVIDENCE / 'FAIL.json').is_file()
    assert not (m.EVIDENCE / 'PASS.json').exists()


@pytest.mark.parametrize('stage', ['census-before', 'inspect-before', 'logs-before',
    'remove-intent', 'remove-result', 'census-after', 'absence-proven'])
@pytest.mark.parametrize('sig', [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_signal_at_transaction_boundary_preserves_exclusion(transaction, monkeypatch, stage, sig):
    calls, _ = transaction
    original = m.Journal.event

    def event(self, name, **fields):
        original(self, name, **fields)
        if name == stage:
            os.kill(os.getpid(), sig)

    monkeypatch.setattr(m.Journal, 'event', event)
    with pytest.raises(m.Error, match='interrupted'):
        m.execute('a' * 40, 'b' * 64)
    assert ('quarantine',) not in calls
    assert (m.EVIDENCE / 'FAIL.json').exists()


def test_capture_failure_before_rm_never_mutates(transaction, monkeypatch):
    calls, _ = transaction
    original = m.Journal.put

    def put(self, name, data):
        if name == 'inspect-before.stdout':
            raise OSError('disk full')
        return original(self, name, data)

    monkeypatch.setattr(m.Journal, 'put', put)
    with pytest.raises(OSError):
        m.execute('a' * 40, 'b' * 64)
    assert not any(c[0] in ('rm', 'quarantine') for c in calls)


def test_failure_capturing_rm_result_leaves_exclusion(transaction, monkeypatch):
    calls, _ = transaction
    original = m.Journal.put

    def put(self, name, data):
        if name == 'remove-result.stdout':
            raise OSError('disk full after daemon mutation')
        return original(self, name, data)

    monkeypatch.setattr(m.Journal, 'put', put)
    with pytest.raises(OSError):
        m.execute('a' * 40, 'b' * 64)
    assert any(c[0] == 'rm' for c in calls)
    assert ('quarantine',) not in calls


def test_short_writes_and_no_replace(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'EVIDENCE', tmp_path / 'evidence')
    j = m.Journal()
    original = os.write
    monkeypatch.setattr(m.os, 'write', lambda fd, data: original(fd, data[:1]))
    try:
        j.put('entry', b'abcd')
        assert (m.EVIDENCE / 'entry').read_bytes() == b'abcd'
        with pytest.raises(FileExistsError):
            j.put('entry', b'replaced')
    finally:
        j.close()


def test_read_file_rejects_symlink_hardlink_and_parent_link(tmp_path):
    file = tmp_path / 'file'
    file.write_bytes(b'bytes')
    link = tmp_path / 'link'
    link.symlink_to(file)
    with pytest.raises(OSError):
        m.read_file(link)
    os.link(file, tmp_path / 'hardlink')
    with pytest.raises(m.Error):
        m.read_file(file)
    real = tmp_path / 'dir'
    real.mkdir()
    parent = tmp_path / 'parent'
    parent.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        m.open_directory(parent)


@pytest.fixture
def quarantine(tmp_path, monkeypatch):
    path = tmp_path / 'exclusion'
    path.write_bytes(b'x' * 269)
    path.chmod(0o600)
    st = path.stat()
    monkeypatch.setattr(m, 'EXCLUSION', path)
    monkeypatch.setattr(m, 'EXCLUSION_SHA', m.sha(path.read_bytes()))
    monkeypatch.setattr(m, 'EXCLUSION_ID', (st.st_dev, st.st_ino))
    monkeypatch.setattr(m, 'EVIDENCE', tmp_path / 'journal')
    # Production UID is 1000; fixture hosts can run pytest under another UID.
    real_checked = m.checked

    def checked(*args):
        data, s = real_checked(*args)
        return data, SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino, st_uid=1000, st_mode=s.st_mode)

    monkeypatch.setattr(m, 'checked', checked)
    return path


def test_quarantine_exact_retention(quarantine):
    journal = m.Journal()
    try:
        with m.Cancellation() as cancellation:
            m.quarantine_exclusion(journal, cancellation)
        assert not quarantine.exists()
        assert (quarantine.parent / m.QUARANTINE / quarantine.name).read_bytes() == b'x' * 269
        assert (m.EVIDENCE / 'exclusion-retained.json').exists()
    finally:
        journal.close()


@pytest.mark.parametrize('stage', ['quarantine-intent', 'quarantined'])
def test_pending_signal_preserves_named_or_quarantined_exclusion(quarantine, monkeypatch, stage):
    journal = m.Journal()
    original = journal.event

    def event(name, **fields):
        original(name, **fields)
        if name == stage:
            os.kill(os.getpid(), signal.SIGTERM)

    monkeypatch.setattr(journal, 'event', event)
    try:
        with m.Cancellation() as cancellation:
            with pytest.raises(m.Error, match='interrupted'):
                m.quarantine_exclusion(journal, cancellation)
        paths = [quarantine, quarantine.parent / m.QUARANTINE / quarantine.name]
        assert sum(p.exists() for p in paths) == 1
        assert next(p for p in paths if p.exists()).read_bytes() == b'x' * 269
    finally:
        journal.close()


def test_quarantine_replacement_is_retained(quarantine, monkeypatch):
    journal = m.Journal()
    original = journal.event

    def event(name, **fields):
        original(name, **fields)
        if name == 'quarantined':
            p = quarantine.parent / m.QUARANTINE / quarantine.name
            p.write_bytes(b'changed')

    monkeypatch.setattr(journal, 'event', event)
    try:
        with m.Cancellation() as cancellation:
            with pytest.raises(m.Error):
                m.quarantine_exclusion(journal, cancellation)
        assert (quarantine.parent / m.QUARANTINE / quarantine.name).read_bytes() == b'changed'
    finally:
        journal.close()


def test_docker_transport_has_fixed_host_and_no_volume_removal(monkeypatch):
    captured = []
    monkeypatch.setattr(m, 'run', lambda args: captured.append(args))
    m.docker('rm', m.CONTAINER)
    assert captured == [['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host',
                         'unix:///var/run/docker.sock', 'rm', m.CONTAINER]]
    assert '-v' not in captured[0] and '--volumes' not in captured[0]
    assert '--no-prune' not in captured[0]


@pytest.mark.parametrize('field,value', [('Id', 'f' * 64), ('Name', '/other'), ('Image', 'other')])
def test_container_identity_rejection(field, value, monkeypatch):
    obj = {'Id': m.CONTAINER, 'Name': '/' + m.NAME, 'Image': m.IMAGE,
           'Config': {'Labels': {'mckernel.owner': m.NONCE}},
           'State': {'Status': 'exited', 'Pid': 0, 'ExitCode': 0, 'Running': False,
                     'OOMKilled': False, 'Paused': False, 'Restarting': False, 'Dead': False},
           'Mounts': [], 'HostConfig': {}}
    monkeypatch.setattr(m, 'read_file', lambda *a: (json.dumps({'terminal_container_info': obj}).encode(), None))
    m.inspect(result(json.dumps([obj]).encode()))
    changed = dict(obj)
    changed[field] = value
    with pytest.raises(m.Error):
        m.inspect(result(json.dumps([changed]).encode()))


@pytest.mark.parametrize('change', ['permutation', 'mutation', 'missing', 'duplicate'])
def test_mounts_are_authenticated_as_unordered_complete_multiset(change, monkeypatch):
    mounts = [
        {'Source': '/src', 'Destination': '/src', 'RW': False, 'Type': 'bind'},
        {'Source': '/work', 'Destination': '/work', 'RW': True, 'Type': 'bind'},
        {'Source': '/work', 'Destination': '/work', 'RW': True, 'Type': 'bind'},
    ]
    obj = {'Id': m.CONTAINER, 'Name': '/' + m.NAME, 'Image': m.IMAGE,
           'Config': {'Labels': {'mckernel.owner': m.NONCE}},
           'State': {'Status': 'exited', 'Pid': 0, 'ExitCode': 0, 'Running': False,
                     'OOMKilled': False, 'Paused': False, 'Restarting': False, 'Dead': False},
           'Mounts': mounts, 'HostConfig': {'RestartPolicy': {'Name': 'no'}}}
    retained = json.loads(json.dumps(obj))
    monkeypatch.setattr(m, 'read_file', lambda *a: (json.dumps({'terminal_container_info': retained}).encode(), None))
    if change == 'permutation':
        obj['Mounts'] = list(reversed(obj['Mounts']))
        assert m.inspect(result(json.dumps([obj]).encode())) == obj
        return
    if change == 'mutation':
        obj['Mounts'][0]['RW'] = True
    elif change == 'missing':
        obj['Mounts'].pop()
    else:
        obj['Mounts'].append(dict(obj['Mounts'][0]))
    with pytest.raises(m.Error, match='container mount/profile changed'):
        m.inspect(result(json.dumps([obj]).encode()))


def test_release_hash_is_external_not_circular():
    source = SOURCE.read_text()
    assert 'RELEASE_HASH_REQUIRED' not in source
    assert "parser.add_argument('--release-sha256', required=True)" in source
    assert "git('show', commit + ':' + PACKET_PATH)" in source
    assert "git('show', commit + ':' + RELEASE_PATH)" in source


def test_bad_release_pins_rejected_without_commands():
    with pytest.raises(m.Error):
        m.release_guard('short', 'short')


@pytest.fixture
def release_fixture(monkeypatch):
    packet = b'exact packet'
    release = {
        'schema': 'mckernel.export26-cleanup-release.v1',
        'status': 'PASS_EXECUTION_EXPORT26_CLEANUP', 'packet_sha256': m.sha(packet),
        'candidate_sha': m.CANDIDATE, 'container_id': m.CONTAINER,
        'container_name': m.NAME, 'owner_nonce': m.NONCE, 'image_id': m.IMAGE,
        'exclusion_sha256': m.EXCLUSION_SHA, 'exclusion_device_inode': '1831:90699',
        'evidence_root': str(m.EVIDENCE), 'log_sha256': m.LOG_SHA, 'invocations': 1,
        'owner_receipt_sha256': m.PINNED_FILES[m.OWNER_RECEIPT],
        'driver_receipt_sha256': m.PINNED_FILES[m.DRIVER_RECEIPT],
    }
    encoded = lambda: json.dumps(release).encode()

    def git(*args):
        if args[0] == 'rev-parse':
            return b'a' * 40 + b'\n'
        if args[0] == 'merge-base':
            return b''
        if args == ('show', 'a' * 40 + ':' + m.RELEASE_PATH):
            return encoded()
        if args == ('show', 'a' * 40 + ':' + m.PACKET_PATH):
            return packet
        raise AssertionError(args)

    def read(path):
        if path == m.REPO / m.RELEASE_PATH:
            return encoded(), None
        if path == m.REPO / m.PACKET_PATH:
            return packet, None
        raise AssertionError(path)

    monkeypatch.setattr(m, 'git', git)
    monkeypatch.setattr(m, 'read_file', read)
    return release, encoded, git, read


def test_committed_release_accepts_exact_pins(release_fixture):
    _, encoded, _, _ = release_fixture
    assert m.release_guard('a' * 40, m.sha(encoded())) == encoded()


@pytest.mark.parametrize('field', ['status', 'packet_sha256', 'candidate_sha', 'container_id',
    'container_name', 'owner_nonce', 'image_id', 'exclusion_sha256', 'exclusion_device_inode',
    'evidence_root', 'log_sha256', 'owner_receipt_sha256', 'driver_receipt_sha256', 'invocations'])
def test_committed_release_rejects_missing_fields(release_fixture, field):
    release, encoded, _, _ = release_fixture
    del release[field]
    with pytest.raises(m.Error, match='release field'):
        m.release_guard('a' * 40, m.sha(encoded()))


@pytest.mark.parametrize('mismatch', ['hash', 'local_release', 'local_helper', 'unfetched'])
def test_release_rejects_uncommitted_or_unfetched_bytes(release_fixture, monkeypatch, mismatch):
    _, encoded, git, read = release_fixture
    if mismatch.startswith('local_'):
        target = m.REPO / (m.RELEASE_PATH if mismatch == 'local_release' else m.PACKET_PATH)
        monkeypatch.setattr(m, 'read_file', lambda p: (b'changed', None) if p == target else read(p))
    elif mismatch == 'unfetched':
        def fail(*args):
            if args[0] == 'merge-base':
                raise m.Error('git authentication failed')
            return git(*args)
        monkeypatch.setattr(m, 'git', fail)
    with pytest.raises(m.Error):
        m.release_guard('a' * 40, '0' * 64 if mismatch == 'hash' else m.sha(encoded()))


def test_exact_client_paths_hashes_and_absent_pids(monkeypatch):
    seen_paths = []
    seen_absent = []
    by_path = {m.OWNER / 'attempt' / name / 'status.json': (pid, m.CLIENT_SHA[name])
               for name, pid in m.CLIENTS.items()}

    def checked(path, expected):
        seen_paths.append(path)
        pid, digest = by_path[path]
        assert digest == expected
        return json.dumps({'pid': pid, 'state': 'exited', 'exit_code': 0}).encode(), None

    monkeypatch.setattr(m, 'checked', checked)
    monkeypatch.setattr(m, 'absent', seen_absent.append)
    m.retired()
    assert set(seen_paths) == set(by_path)
    assert seen_absent == [m.LEASE] + ['/proc/' + str(pid) for pid in (2420278, *m.CLIENTS.values())]


def test_lease_permission_error_is_not_absence(monkeypatch):
    def denied(path):
        raise PermissionError('procfs denied')
    monkeypatch.setattr(m.os, 'lstat', denied)
    with pytest.raises(PermissionError):
        m.absent(m.LEASE)


@pytest.mark.parametrize('stage', ['quarantined', 'exclusion-retained'])
def test_quarantine_publication_failure_retains_exact_bytes(quarantine, monkeypatch, stage):
    journal = m.Journal()
    original = journal.event

    def event(name, **fields):
        original(name, **fields)
        if name == stage:
            raise OSError('injected failure after ' + stage)

    monkeypatch.setattr(journal, 'event', event)
    try:
        with m.Cancellation() as cancellation:
            with pytest.raises(OSError):
                m.quarantine_exclusion(journal, cancellation)
        retained = quarantine.parent / m.QUARANTINE / quarantine.name
        assert not quarantine.exists()
        assert retained.read_bytes() == b'x' * 269
        m.exclusion(retained)
    finally:
        journal.close()


def test_quarantine_directory_fsync_failure_retains_exact_bytes(quarantine, monkeypatch):
    journal = m.Journal()
    original_fsync = os.fsync
    original_rename = m.rename_noreplace
    moved = []

    def rename(*args):
        original_rename(*args)
        moved.append(args[2])

    def fsync(fd):
        if moved and fd == moved[0]:
            raise OSError('injected quarantine fsync failure')
        original_fsync(fd)

    monkeypatch.setattr(m, 'rename_noreplace', rename)
    monkeypatch.setattr(m.os, 'fsync', fsync)
    try:
        with m.Cancellation() as cancellation:
            with pytest.raises(OSError):
                m.quarantine_exclusion(journal, cancellation)
        retained = quarantine.parent / m.QUARANTINE / quarantine.name
        assert retained.read_bytes() == b'x' * 269
        m.exclusion(retained)
    finally:
        journal.close()


@pytest.mark.parametrize('stage', ['completion_snapshot', 'PASS_before', 'PASS_after',
                                  'PASS_fsync', 'close'])
def test_finalization_failures_keep_exact_exclusion(transaction, tmp_path, monkeypatch, stage):
    path = tmp_path / 'original-exclusion'
    payload = b'exact exclusion evidence retained through finalization'
    path.write_bytes(payload)
    original_stat = path.stat()
    monkeypatch.setattr(m, 'EXCLUSION', path)
    monkeypatch.setattr(m, 'quarantine_exclusion', REAL_QUARANTINE)
    original_event = m.Journal.event
    original_close = m.Journal.close
    original_snapshot = m.snapshot
    original_fsync = os.fsync

    def event(self, name, **fields):
        if name == 'PASS' and stage == 'PASS_before':
            raise OSError('injected failure before PASS publication')
        original_event(self, name, **fields)
        if name == 'PASS' and stage == 'PASS_after':
            raise OSError('injected failure after PASS publication')

    def snapshot():
        if stage == 'completion_snapshot' and (m.EVIDENCE / 'exclusion-retained.json').exists():
            raise OSError('injected completion snapshot failure')
        return original_snapshot()

    def fsync(fd):
        if stage == 'PASS_fsync' and (m.EVIDENCE / 'PASS.json').exists():
            raise OSError('injected PASS fsync failure')
        original_fsync(fd)

    def close(self):
        original_close(self)
        if stage == 'close':
            raise OSError('injected close failure')

    monkeypatch.setattr(m.Journal, 'event', event)
    monkeypatch.setattr(m.Journal, 'close', close)
    monkeypatch.setattr(m, 'snapshot', snapshot)
    monkeypatch.setattr(m.os, 'fsync', fsync)
    with pytest.raises(OSError):
        m.execute('a' * 40, 'b' * 64)
    retained = path.parent / m.QUARANTINE / path.name
    assert not path.exists()
    assert retained.read_bytes() == payload
    assert (retained.stat().st_dev, retained.stat().st_ino) == (original_stat.st_dev, original_stat.st_ino)


def test_source_has_no_exclusion_deletion_operation():
    source = SOURCE.read_text()
    assert 'os.unlink(' not in source
    assert 'os.remove(' not in source
    assert 'os.rmdir(' not in source


@pytest.fixture
def exact_hardlink(tmp_path, monkeypatch):
    primary = tmp_path / 'primary'
    alias = tmp_path / 'alias'
    primary.write_bytes(b'exact historical read-only bind')
    primary.chmod(0o600)
    os.link(primary, alias)
    st = primary.stat()
    monkeypatch.setattr(m, 'HARDLINK_PATHS', (primary, alias))
    monkeypatch.setattr(m, 'HARDLINK_METADATA',
                        (st.st_dev, st.st_ino, 2, st.st_size, 0o600, st.st_uid))
    monkeypatch.setattr(m, 'HARDLINK_SHA', m.sha(primary.read_bytes()))
    return primary, alias


def test_exact_hardlink_pair_authenticates_each_name(exact_hardlink):
    primary, alias = exact_hardlink
    assert m.read_file(primary)[0] == primary.read_bytes()
    assert m.read_file(alias)[0] == primary.read_bytes()


@pytest.mark.parametrize('change', ['extra_alias', 'missing_alias', 'repointed_alias',
                                   'symlink_alias', 'bytes', 'mode'])
def test_exact_hardlink_rejects_alias_or_file_drift(exact_hardlink, tmp_path, change):
    primary, alias = exact_hardlink
    if change == 'extra_alias':
        os.link(primary, tmp_path / 'third')
    elif change == 'missing_alias':
        alias.unlink()
    elif change == 'repointed_alias':
        payload = alias.read_bytes()
        alias.unlink()
        alias.write_bytes(payload)
        os.link(primary, tmp_path / 'unapproved-primary-name')
        os.link(alias, tmp_path / 'unapproved-alias-name')
    elif change == 'symlink_alias':
        alias.unlink()
        alias.symlink_to(primary)
        os.link(primary, tmp_path / 'unapproved-primary-name')
    elif change == 'bytes':
        primary.write_bytes(b'wrong' + primary.read_bytes()[5:])
    else:
        primary.chmod(0o644)
    with pytest.raises((m.Error, OSError)):
        m.read_file(primary)


@pytest.mark.parametrize('field', range(6))
def test_exact_hardlink_requires_every_metadata_field(exact_hardlink, monkeypatch, field):
    primary, _ = exact_hardlink
    expected = list(m.HARDLINK_METADATA)
    expected[field] += 1
    monkeypatch.setattr(m, 'HARDLINK_METADATA', tuple(expected))
    with pytest.raises(m.Error, match='hardlink bind identity'):
        m.read_file(primary)


def test_hardlink_exception_does_not_admit_other_pairs(exact_hardlink, tmp_path):
    other = tmp_path / 'other'
    other.write_bytes(b'unapproved')
    os.link(other, tmp_path / 'other-alias')
    with pytest.raises(m.Error, match='nonordinary'):
        m.read_file(other)


def test_hardlink_pair_rechecked_after_first_read(exact_hardlink, monkeypatch):
    primary, alias = exact_hardlink
    original = m._read_stable_file
    calls = []

    def changed(path, limit, links):
        answer = original(path, limit, links)
        calls.append(path)
        if len(calls) == 2:
            primary.write_bytes(b'x' * primary.stat().st_size)
        return answer

    monkeypatch.setattr(m, '_read_stable_file', changed)
    with pytest.raises(m.Error, match='changed during authentication'):
        m.read_file(primary)
