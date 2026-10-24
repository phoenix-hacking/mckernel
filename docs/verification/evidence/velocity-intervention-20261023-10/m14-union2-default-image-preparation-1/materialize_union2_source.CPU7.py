#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Ordinary exact known-input source copy: ELEVEN accepted canonical compute postimages over prior idle+memory source.
No Git command, compiler, Docker, root, guest or active source/build modification.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import stat
import time

REPO = Path('/home/holden/mckernel')
OUT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/source-materialization-attempt-1')
SOURCE = BASE / 'materialized-source'
DEST = OUT / 'materialized-source'
AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/CANONICAL-SOURCE-SUCCESSOR-BASIS.CHECKPOINT-PENDING.json')
BASE_CANONICAL_SHA = '77fd79cde7d48ceb65aaf9de2ff8be78005274f22031fe12c58d8309173c58a4'
POST = {'kernel/mem.c': '4d2d267cacb48a69179d9b29dec5d905748143210e0f6c7d555e0ac508b419f3', 'kernel/rust/mem_helpers.rs': 'be693dec5e53b20f06f7963b7418a7c0dff68cbecaaa2360e291d8542784e045', 'kernel/process.c': '7ab29dad607ac06e9548065f4395c6e870359558a2777844c1052d67e046ca13', 'kernel/rust/process_helpers.rs': '5bf085bfa3f60217abacbda380e80d35d2fd56922c0e82f82dbab1d5fe09d4d1', 'kernel/syscall.c': '07af5efb4af2754988376301d19887ea90743b8f304455b7df980738f2629399', 'arch/x86_64/kernel/cpu.c': '5574c151cef8d26fa14e3eac72d54b55703be153e4f147f831c5a9e9b63c70bc', 'kernel/rust/x86_cpu_helpers.rs': 'a44a391c7eb461b82cb181089941f52e8845ae90b04d34319aff6437deebb3e4', 'arch/x86_64/kernel/memory.c': 'ceed123214cd293f5afefd21dd071e39aa824cf3424cc6355a841c1ae5467f39', 'kernel/rust/x86_memory_helpers.rs': '087240006b3f1b99c844c77c1c645118710bf34f53546637eb12d54215822092', 'arch/x86_64/kernel/syscall.c': 'd876e0b24f789372e6747fee7c554a53a3deaa9cee7034d7096374c2dff34ad6', 'kernel/rust/syscall_policy.rs': 'c5d6ddd9ce210ffd51f0e84c3feefddcf4d115044ced76018b9e946aad9cb6f5'}
MAX_GROWTH = 256 << 20
EXTRA = 16 << 20
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())


def main():
    begin = time.monotonic()
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {7}, 'ordinary CPU7 grant required')
    need(not os.path.lexists(DEST), 'fresh coherent destination required')
    baseline = json.loads((BASE / 'source-inputs.json').read_text())
    need(sha(canonical(baseline)) == BASE_CANONICAL_SHA, 'accepted exact base source manifest')
    authority_raw = AUTHORITY.read_bytes();authority = json.loads(authority_raw)
    need(authority['status'] == 'EXACT_ELEVEN_CURRENT_UNION_POSTIMAGES_SELECTED_FOR_DEFAULT_IMAGE_SUCCESSOR_PREPARATION' and {p:row['after']['sha256'] for p,row in authority['changes'].items()} == POST,
         'root-bound eleven accepted canonical postimages; ordinary execution grant separate')
    document = copy.deepcopy(baseline)
    changed = []
    for relative, checksum in POST.items():
        need(sha((REPO / relative).read_bytes()) == checksum, 'canonical integrated postimage changed: ' + relative)
        changed.append(dict(path=relative, before_sha256=baseline['repository_files'][relative], after_sha256=checksum))
        document['repository_files'][relative] = checksum
        document['materialized_repository_files'][relative] = checksum
    derivation = dict(base_manifest_canonical_sha256=BASE_CANONICAL_SHA,
                      base_source_derivative_sha256=baseline['source_derivative_sha256'],
                      canonical_integration_sha256=sha(authority_raw), latest_memory_two_source_delta=changed,
                      repository_files=document['repository_files'], gitlinks=document['gitlinks'],
                      ihk_overlay=document['ihk_overlay'])
    document['schema'] = 'mckernel.m14-combined-production-thin-inputs.v1'
    document['source_derivative_sha256'] = sha(canonical(derivation))
    document['latest_memory_callback_overlay'] = derivation
    materialization = {key: document[key] for key in (
        'source_derivative_sha256', 'materialized_repository_files', 'materialized_modes',
        'retained_ihk_git_metadata', 'omitted_repository_files', 'omitted_main_git_metadata',
        'materialized_kinds', 'materialized_symlinks')}
    document['materialization_sha256'] = sha(canonical(materialization))
    write('source-inputs.json', document)
    expected = dict(document['materialized_repository_files'])
    expected.update({path: row['sha256'] for path, row in document['retained_ihk_git_metadata'].items()})
    links = document['materialized_symlinks'];modes = document['materialized_modes']
    need(set(expected) == set(modes) and len(expected) == 6959 and len(links) == 49,
         'exact accepted finite source entry set')
    old_rows = [json.loads(line) for line in (BASE / 'materialization-journal.jsonl').read_text().splitlines()]
    sizes = {row['path']: row['size'] for row in old_rows}
    need(set(sizes) == set(expected), 'prior exact materialization journal set')
    for relative in POST:
        sizes[relative] = (REPO / relative).stat().st_size
    total = sum(sizes.values());need(total <= MAX_GROWTH, 'bounded whole source growth')
    host = os.statvfs(OUT);scratch = os.statvfs('/home/holden/mckernel-work/scratch')
    need(host.f_bavail * host.f_frsize >= 16 * 2**30 + total + EXTRA, 'HOST floor plus complete source growth/capture')
    need(scratch.f_bavail * scratch.f_frsize >= 12 * 2**30, 'scratch floor preserved; no scratch writes')
    admission = dict(host_available=host.f_bavail*host.f_frsize, scratch_available=scratch.f_bavail*scratch.f_frsize,
                     source_growth_bytes=total, max_source_growth_bytes=MAX_GROWTH, capture_extra_bytes=EXTRA)
    write('admission.json', admission)
    DEST.mkdir(mode=0o700)
    for relative in document['gitlinks']:
        if relative != 'ihk':
            (DEST / relative).mkdir(parents=True, exist_ok=True)
    copied = 0
    with (OUT / 'materialization-journal.jsonl').open('x') as journal:
        for relative, checksum in sorted(expected.items()):
            rel = Path(relative)
            need(not rel.is_absolute() and '..' not in rel.parts and '.' not in rel.parts, 'exact safe source relative path')
            source = (REPO if relative in POST else SOURCE) / relative
            destination = DEST / relative;destination.parent.mkdir(parents=True, exist_ok=True)
            before = source.lstat()
            if relative in links:
                row = links[relative];target = os.readlink(source);raw = os.fsencode(target)
                need(stat.S_ISLNK(before.st_mode) and target == row['target'] == Path(target).name
                     and sha(raw) == checksum and stat.S_IMODE(before.st_mode) == 0o777, 'exact tracked symlink')
                destination.symlink_to(target)
                entry = dict(path=relative, sha256=checksum, size=len(raw), kind='symlink', target=target)
            else:
                need(stat.S_ISREG(before.st_mode) and source.resolve() == source and before.st_size == sizes[relative],
                     'regular known source size/path: ' + relative)
                fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                digest = hashlib.sha256();count = 0
                with os.fdopen(fd, 'rb') as inp, destination.open('xb') as output:
                    opened = os.fstat(inp.fileno())
                    for block in iter(lambda: inp.read(1 << 20), b''):
                        digest.update(block);output.write(block);count += len(block)
                    output.flush();os.fsync(output.fileno())
                    closed = os.fstat(inp.fileno())
                after = source.lstat()
                fields = ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
                need(all(getattr(before,key)==getattr(opened,key)==getattr(closed,key)==getattr(after,key) for key in fields)
                     and count == sizes[relative] and digest.hexdigest() == checksum,
                     'stable exact copy/hash: ' + relative)
                destination.chmod(modes[relative])
                need(destination.stat().st_nlink == 1, 'private copy, never shared hardlink')
                entry = dict(path=relative, sha256=checksum, size=count, kind='file')
            journal.write(json.dumps(entry, sort_keys=True) + '\n');journal.flush();copied += entry['size']
    # A names/type/mode closure check reads the newly owned tree only; copied
    # file bytes were hash-checked in their one copy pass, not recursively again.
    observed = set()
    for directory, directories, names in os.walk(DEST, followlinks=False):
        for name in names:
            path = Path(directory)/name;relative=str(path.relative_to(DEST));observed.add(relative)
            meta=path.lstat()
            need(relative in expected and stat.S_IMODE(meta.st_mode)==modes[relative], 'new tree file/mode closure')
            need(stat.S_ISLNK(meta.st_mode) if relative in links else stat.S_ISREG(meta.st_mode), 'new tree kind closure')
        for name in directories:
            need(not (Path(directory)/name).is_symlink(), 'no directory symlinks')
    need(observed == set(expected), 'complete copied entry closure')
    for relative,row in links.items():
        destination=DEST/relative;target=destination.parent/row['target']
        need(target.is_file() and not target.is_symlink() and row['target_path'] in expected
             and expected[row['target_path']]==row['target_sha256'], 'tracked symlink targets use copied verified files')
    result = dict(scope=SCOPE, status='PASS_COHERENT_CURRENT_ELEVEN_UNION_SOURCE_MATERIALIZATION_ONLY',
                  source_root=str(DEST), source_entries=len(expected), regular_files=len(expected)-len(links),
                  tracked_symlinks=len(links), copied_bytes=copied, source_derivative_sha256=document['source_derivative_sha256'],
                  materialization_sha256=document['materialization_sha256'],source_manifest_canonical_sha256=sha(canonical(document)),
                  base_source_manifest_canonical_sha256=BASE_CANONICAL_SHA,canonical_integration_sha256=sha(authority_raw),
                  changed_source_files=changed, all_other_known_source_and_metadata_preserved=True,
                  canonical_source_written=False,frozen_image_or_build_written=False,builds=0,guests=0,seconds=time.monotonic()-begin)
    write('MATERIALIZATION-RESULT.json', result)
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
