#!/usr/bin/env python3
"""Retain only reviewed source/metadata; never import or run test sources."""
from pathlib import Path
import hashlib
import json
import os
import stat
import tarfile

REPO = Path('/home/holden/mckernel')
CAPTURE = Path('/tmp/stability-application-request-decoder-source-20260913-yn1omu0r')
EVIDENCE = REPO / 'docs/verification/evidence'
BASENAME = 'stability-application-request-decoder-source-20260913-1'


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_size < 16 * 1024 * 1024, 'nonregular/oversized source')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while True:
            data = stream.read(65536)
            if not data:
                break
            digest.update(data)
            size += len(data)
            require(size < 16 * 1024 * 1024, 'source grew past bound')
    after = path.lstat()
    require((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'source changed')
    return {'path': str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
            'size': size, 'sha256': digest.hexdigest()}


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def inventory():
    rows = []
    content_size = 0
    for path in [CAPTURE] + sorted(CAPTURE.rglob('*')):
        require(len(rows) < 256, 'source member bound exceeded')
        info = path.lstat()
        row = {'name': str(path.relative_to(CAPTURE.parent)), 'mode': stat.S_IMODE(info.st_mode)}
        if stat.S_ISDIR(info.st_mode):
            row.update(type='directory', size=0)
        else:
            require(stat.S_ISREG(info.st_mode), 'source tree contains a link or special object')
            item = identity(path)
            row.update(type='file', size=item['size'], sha256=item['sha256'])
            content_size += item['size']
            require(content_size < 16 * 1024 * 1024, 'aggregate source size exceeds bound')
        rows.append(row)
    return rows


def main():
    review = json.loads((CAPTURE / 'review.json').read_bytes())
    require(review['status'] == 'PASS_BOUNDED_SOURCE_REVIEW_ONLY', 'reviews not ready')
    for item in review['frozen_inputs']:
        require(identity(REPO / item['path']) == item, 'reviewed source drift: ' + item['path'])
    before = inventory()
    archive = EVIDENCE / (BASENAME + '.tar.gz')
    with tarfile.open(archive, 'x:gz', format=tarfile.PAX_FORMAT) as output:
        for row in before:
            source = CAPTURE.parent / row['name']
            output.add(source, arcname=row['name'], recursive=False)
    with archive.open('rb') as stream:
        os.fsync(stream.fileno())
    actual = []
    with tarfile.open(archive, 'r:gz') as source:
        for member in source:
            require(len(actual) < 256 and member.name not in {r['name'] for r in actual}, 'duplicate/extra member')
            row = {'name': member.name, 'mode': member.mode}
            if member.isdir():
                row.update(type='directory', size=0)
            else:
                require(member.isfile(), 'unexpected archive member type')
                stream = source.extractfile(member)
                require(stream is not None, 'missing archived content')
                digest = hashlib.sha256()
                size = 0
                while True:
                    block = stream.read(65536)
                    if not block:
                        break
                    digest.update(block)
                    size += len(block)
                    require(size < 16 * 1024 * 1024, 'archived content exceeds bound')
                require(size == member.size, 'archived content size differs')
                row.update(type='file', size=size, sha256=digest.hexdigest())
            actual.append(row)
    require(actual == before, 'decoded archive members differ')
    require(inventory() == before, 'original source changed during retention')
    for item in review['frozen_inputs']:
        require(identity(REPO / item['path']) == item, 'reviewed source changed during retention')
    manifest = EVIDENCE / (BASENAME + '.members.json')
    save(manifest, {'schema_version': 1, 'kind': 'source-archive-members', 'members': before,
                    'all_members_verified': True, 'originals_unchanged': True})
    helper_copy = EVIDENCE / 'stability-application-request-decoder-retention-20260913-1.py'
    with helper_copy.open('xb') as stream:
        stream.write(Path(__file__).read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    summary = {
        **review,
        'source_capture': str(CAPTURE), 'source_capture_review': identity(CAPTURE / 'review.json'),
        'original_sources_and_reviews_preserved': True, 'originals_unchanged': True,
        'all_members_verified': True, 'helper': identity(Path(__file__)),
        'retained_helper': identity(helper_copy),
        'archive': identity(archive), 'member_manifest': identity(manifest),
        'member_count': len(before), 'regular_file_count': sum(r['type'] == 'file' for r in before),
        'content_bytes': sum(r['size'] for r in before),
    }
    publication = REPO / 'docs/verification/stability-application-request-decoder-review-20260913.json'
    save(publication, summary)
    save(Path(__file__).parent / 'record.json', {'status': 'PASS_SOURCE_RETENTION_ONLY', 'publication': identity(publication)})
    print(json.dumps({'publication': identity(publication), 'archive': identity(archive),
                      'member_manifest': identity(manifest), 'members': len(before)}, indent=2))


if __name__ == '__main__':
    main()
