#!/usr/bin/env python3
"""Verify the pushed drafting-only handoff using exact fetched Git objects.

Host invocation after root commit/push: python3 -B THIS_HELPER FRESH_ATTEMPT
No commit, push, checkout, reset, clean, build, guest or artifact deletion.
Fetch updates only Git object/FETCH_HEAD metadata, as in the prior verifier.

Only JSON directly under docs/verification/ is an evidence manifest for
recursive reference checking. Catalogs, packets and retained bounded-context
JSON under docs/verification/evidence/ are fetched whole blobs: their planned
payload paths are specifications, not claims that payload files already exist.
Manifest identity rows assert path/size/sha256; metadata validation is separate.
"""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys

assert len(sys.argv) == 2 and re.fullmatch(r'[1-9][0-9]*', sys.argv[1])
repo = Path('/home/holden/mckernel')
scratch = Path('/home/holden/mckernel-work/scratch')
out = scratch / ('ultra-final-github-20260909-' + sys.argv[1] + '.json')
report_stream = out.open('x')
branch = 'refs/heads/codex/local-native-staging-repair'
repository_url = 'https://github.com/phoenix-hacking/mckernel.git'
git_environment = dict(os.environ, GIT_TERMINAL_PROMPT='0')
release_path = 'docs/verification/ultra-drafting-handoff-20260909.json'
checkpoint_path = 'docs/verification/ultra-final-checkpoint-20260909.json'
queue_path = 'scripts/application-tests/draft-queue.json'
record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
    scope='Exact fetched GitHub blobs and drafting-only release; no new application/runtime acceptance',
    recursive_manifest_scope='JSON directly under docs/verification/ only; packet/catalog/retained context JSON is checked as complete fetched blobs, not interpreted as evidence manifests',
    release_manifest=release_path, final_checkpoint=checkpoint_path,
    verified_blobs=[], verified_gitlinks=[], deleted_paths_verified=[],
    manifest_identity_checks=[], manifest_paths=[], skipped_absolute_references=[],
    runtime_execution_authorized=False, application_tests_executed=0)
trees, checked_worktrees = {}, set()
paths, pending_manifests, parsed_manifests = set(), [], set()
absolute_seen = set()


def save():
    report_stream.seek(0)
    report_stream.truncate()
    json.dump(record, report_stream, indent=2, sort_keys=True)
    report_stream.write('\n')
    report_stream.flush()
    os.fsync(report_stream.fileno())


def git(*arguments, directory=repo):
    return subprocess.check_output(['git', *arguments], cwd=str(directory), env=git_environment, timeout=180)


def clean(directory):
    if str(directory) in checked_worktrees:
        return
    status = git('status', '--porcelain', '--untracked-files=all', '--ignore-submodules=none', directory=directory)
    assert status == b'', ('dirty worktree', str(directory), status.decode(errors='replace'))
    checked_worktrees.add(str(directory))


def safe_relative(value):
    assert isinstance(value, str) and value and '\x00' not in value and '\\' not in value, value
    path = PurePosixPath(value)
    assert not path.is_absolute() and value == str(path), value
    assert path.parts and all(part not in ('..', '.', '') for part in path.parts), value
    return value


def local_identity(relative):
    path = repo / safe_relative(relative)
    digest = hashlib.sha256()
    size = 0
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        data = os.fsencode(os.readlink(path))
        return dict(path=relative, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert stat.S_ISREG(info.st_mode), ('not a regular repository file', relative)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
            size += len(chunk)
    return dict(path=relative, size=size, sha256=digest.hexdigest())


def tree(directory, commit):
    key = (str(directory), commit)
    if key not in trees:
        result = {}
        for entry in git('ls-tree', '-r', '-z', commit, directory=directory).split(b'\0'):
            if not entry:
                continue
            metadata, path = entry.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            name = os.fsdecode(path)
            assert name not in result
            result[name] = dict(mode=mode, kind=kind, blob=blob)
        trees[key] = result
    return trees[key]


def lookup(relative):
    """Resolve through exact fetched gitlinks, never a submodule branch tip."""
    remaining, directory, commit, prefix = safe_relative(relative), repo, fetched, ''
    while True:
        entries = tree(directory, commit)
        if remaining in entries:
            return directory, commit, remaining, entries[remaining], prefix
        parents = [name for name, entry in entries.items()
                   if entry['kind'] == 'commit' and remaining.startswith(name + '/')]
        assert len(parents) == 1, ('missing or ambiguous fetched path', relative, parents)
        name = parents[0]
        selected = entries[name]['blob']
        directory = directory / name
        assert git('rev-parse', 'HEAD', directory=directory).decode().strip() == selected, ('gitlink mismatch', relative)
        clean(directory)
        prefix += name + '/'
        remaining = remaining[len(name) + 1:]
        commit = selected


def add_path(value):
    relative = safe_relative(value)
    paths.add(relative)
    # The repository stores explicit evidence manifests directly in this
    # directory. Nested evidence JSON may instead be a saved bounded context
    # containing uncreated payload_contract.path values; never walk that data.
    if is_evidence_manifest(relative) and relative not in parsed_manifests:
        pending_manifests.append(relative)


def is_evidence_manifest(relative):
    path = PurePosixPath(relative)
    return path.parent == PurePosixPath('docs/verification') and path.suffix == '.json'


def walk(value, manifest, pointer='$'):
    assert is_evidence_manifest(manifest), ('not an explicit evidence manifest', manifest)
    if isinstance(value, dict):
        if isinstance(value.get('path'), str):
            path = value['path']
            if path.startswith('/'):
                key = (manifest, path)
                if key not in absolute_seen:
                    absolute_seen.add(key)
                    record['skipped_absolute_references'].append(dict(manifest=manifest, path=path,
                        reason='Absolute scratch/runtime/host provenance is not a repository blob; retained relative artifacts are verified independently'))
            elif 'sha256' in value or 'size' in value:
                assert {'path', 'size', 'sha256'} <= value.keys(), ('incomplete manifest identity', manifest, pointer)
                add_path(path)
                assert isinstance(value['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', value['sha256']), (manifest, pointer)
                actual = local_identity(path)
                assert actual['sha256'] == value['sha256'], (manifest, pointer, path, 'sha256')
                assert type(value['size']) is int and actual['size'] == value['size'], (manifest, pointer, path, 'size')
                record['manifest_identity_checks'].append(dict(manifest=manifest, pointer=pointer, **actual))
        for key, item in value.items():
            # Only an actual identity row makes an arbitrary 'path' field a
            # repository identity. Bare path selectors can describe planned
            # test payloads and are not recursive evidence references.
            if key != 'path':
                walk(item, manifest, pointer + '/' + str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, manifest, pointer + '/' + str(index))
    elif isinstance(value, str):
        # Also retain unhashed canonical references such as archive part lists
        # and reference_manifest strings. Never treat prose or argv templates
        # as paths. Only the manifest's actual identity rows assert a digest.
        if re.fullmatch(r'(?:docs|scripts|kernel|arch|host-kernel|lib|executer|ihk)/[A-Za-z0-9_./+-]+', value):
            add_path(value)
        elif value in ('AGENTS.md', 'goal.txt', 'kernel.log'):
            add_path(value)


def verify_fetched(relative):
    directory, commit, inside, entry, prefix = lookup(relative)
    path = repo / relative
    if entry['kind'] == 'commit':
        assert entry['mode'] == '160000' and path.is_dir(), relative
        actual = git('rev-parse', 'HEAD', directory=path).decode().strip()
        assert actual == entry['blob'], ('gitlink mismatch', relative, actual, entry['blob'])
        clean(path)
        record['verified_gitlinks'].append(dict(path=relative, gitlink=actual, parent_commit=commit))
        return
    assert entry['kind'] == 'blob' and entry['mode'] in ('100644', '100755', '120000'), (relative, entry)
    info = path.lstat()
    if entry['mode'] == '120000':
        assert stat.S_ISLNK(info.st_mode), relative
        current = io.BytesIO(os.fsencode(os.readlink(path)))
    else:
        assert stat.S_ISREG(info.st_mode), relative
        assert bool(info.st_mode & 0o111) == (entry['mode'] == '100755'), ('executable mode mismatch', relative)
        current = path.open('rb')
    digest, size = hashlib.sha256(), 0
    process = subprocess.Popen(['git', 'cat-file', 'blob', entry['blob']], cwd=str(directory),
                               env=git_environment, stdout=subprocess.PIPE)
    try:
        with current:
            while True:
                chunk = process.stdout.read(1 << 20)
                if not chunk:
                    break
                assert current.read(len(chunk)) == chunk, ('fetched/local byte mismatch', relative, size)
                digest.update(chunk)
                size += len(chunk)
            assert current.read(1) == b'', ('extra local bytes', relative)
        process.stdout.close()
        assert process.wait(timeout=30) == 0, relative
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=30)
    row = dict(path=relative, size=size, sha256=digest.hexdigest(), git_blob=entry['blob'], git_mode=entry['mode'])
    if prefix:
        row.update(submodule=prefix.rstrip('/'), parent_gitlink=commit)
    record['verified_blobs'].append(row)


try:
    save()
    clean(repo)
    assert git('remote', 'get-url', 'origin').decode().strip() == repository_url, 'origin is not the expected GitHub repository'
    assert git('symbolic-ref', '-q', 'HEAD').decode().strip() == branch
    commit = git('rev-parse', 'HEAD').decode().strip()
    baseline = git('rev-parse', '484e429^{commit}').decode().strip()
    assert subprocess.run(['git', 'merge-base', '--is-ancestor', baseline, commit], cwd=str(repo),
                          env=git_environment, timeout=60).returncode == 0
    remote = git('ls-remote', 'origin', branch).decode().split()
    assert remote == [commit, branch], ('remote branch does not equal local HEAD', remote, commit)
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', branch], cwd=str(repo),
                   env=git_environment, check=True, timeout=300)
    fetched = git('rev-parse', 'FETCH_HEAD').decode().strip()
    assert fetched == commit, (fetched, commit)
    record.update(commit=commit, source_baseline=baseline, repository_url=repository_url,
                  remote_ref=remote, fetch_head=fetched,
                  verification_helper=local_identity(str(Path(__file__).resolve().relative_to(repo)))
                  if Path(__file__).resolve().is_relative_to(repo) else
                  dict(path=str(Path(__file__).resolve()), sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    fetched_tree = tree(repo, fetched)
    assert fetched_tree['ihk']['kind'] == 'commit' and fetched_tree['ihk']['mode'] == '160000'
    paths.update(['AGENTS.md', 'goal.txt', 'kernel.log', 'ihk', release_path, checkpoint_path])
    for path, entry in fetched_tree.items():
        if path.startswith('scripts/application-tests/'):
            paths.add(path)
        if path.startswith('docs/verification/ultra-') and path.endswith(('.json', '.md')):
            add_path(path)
    changed = git('diff', '--name-status', '--no-renames', '-z', baseline, fetched).split(b'\0')
    if changed[-1:] == [b'']:
        changed.pop()
    assert len(changed) % 2 == 0
    for index in range(0, len(changed), 2):
        status, path = changed[index].decode(), os.fsdecode(changed[index + 1])
        safe_relative(path)
        if status == 'D':
            assert path not in fetched_tree and not os.path.lexists(repo / path), ('deleted path persists', path)
            record['deleted_paths_verified'].append(dict(path=path, absent_at=fetched))
        else:
            assert status in ('A', 'M', 'T'), (status, path)
            add_path(path)

    release = json.loads((repo / release_path).read_text())
    required = dict(schema_version=1, status='PASS', release='released-for-drafting',
        mode='draft-only', drafting_only=True, execution_enabled=False,
        runtime_execution_authorized=False, logical_case_count=273, packet_count=97, vector_case_count=56)
    for key, expected in required.items():
        assert type(release.get(key)) is type(expected) and release[key] == expected, ('release contract', key, release.get(key))
    for key, expected_path in [('final_checkpoint', checkpoint_path), ('queue', queue_path)]:
        row = release[key]
        assert {'path', 'size', 'sha256'} <= row.keys() and row['path'] == expected_path, key
    helper = release['verification_helper']
    assert {'path', 'size', 'sha256'} <= helper.keys()
    assert helper['path'].startswith('docs/verification/evidence/') and helper['path'].endswith('.py')
    assert (repo / safe_relative(helper['path'])).read_bytes() == Path(__file__).read_bytes(), 'executed helper differs from retained GitHub helper'
    checkpoint = json.loads((repo / checkpoint_path).read_text())
    assert checkpoint['status'] == 'PASS' and checkpoint['runtime_execution_authorized'] is False
    assert len(checkpoint['native_compiler_bindings']) == 57
    assert len({row['path'] for row in checkpoint['guest_production_bindings']}) == 44
    queue = json.loads((repo / queue_path).read_text())
    assert queue['review_state'] == queue['status'] == 'released-for-drafting'
    assert queue['mode'] == 'draft-only' and queue['execution_enabled'] is False
    assert queue['packet_count'] == len(queue['packets']) == 97 and queue['logical_case_count'] == 273
    catalog = json.loads((repo / 'scripts/application-tests/cases.json').read_text())
    assert catalog['logical_case_count'] == len(catalog['cases']) == 273
    assert sum(case['id'].startswith('vector.') for case in catalog['cases']) == 56
    packet_paths = sorted(path for path in paths if re.fullmatch(r'scripts/application-tests/packets/packet-[0-9]{3}\.json', path))
    assert len(packet_paths) == 97
    for path in packet_paths:
        packet = json.loads((repo / path).read_text())
        assert packet['mode'] == 'draft-only' and packet['execution_enabled'] is False, path
    add_path(release_path)
    add_path(checkpoint_path)
    while pending_manifests:
        path = pending_manifests.pop()
        if path in parsed_manifests:
            continue
        parsed_manifests.add(path)
        state = json.loads((repo / path).read_text())
        record['manifest_paths'].append(path)
        walk(state, path)
    save()
    for index, path in enumerate(sorted(paths), 1):
        verify_fetched(path)
        if index % 16 == 0:
            print('VERIFIED', index, 'of', len(paths), path, flush=True)
            save()
    checked_worktrees.clear()
    clean(repo)
    for row in record['verified_gitlinks']:
        clean(repo / row['path'])
    assert git('rev-parse', 'HEAD').decode().strip() == commit
    assert git('rev-parse', 'FETCH_HEAD').decode().strip() == fetched
    assert git('remote', 'get-url', 'origin').decode().strip() == repository_url
    assert git('ls-remote', 'origin', branch).decode().split() == [commit, branch]
    record.update(status='PASS', drafting_release_verified=True, logical_case_count=273,
                  packet_count=97, vector_case_count=56, runtime_execution_authorized=False,
                  application_runtime_acceptance_asserted=False)
except BaseException as error:
    record.update(status='FAIL', error=str(error), drafting_release_verified=False)
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    report_stream.close()
    print(record['status'], record.get('commit'), 'exact fetched blobs', len(record['verified_blobs']), str(out), flush=True)
