import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile

REPO = Path('/home/holden/mckernel')
CAPTURE = Path('/tmp/stability-payload-source-retention-20260913-5t5_4705')
GROUPS = [
    ('stability-runnable-thread-payload-source-20260913-1', {
        'source': Path('/tmp/stability-runnable-thread-payload-source-20260913-n8qknrbi'),
        'independent-c-review': Path('/tmp/stability-runnable-payload-independent-review-20260913-p0p_zua0'),
        'independent-owner-review': Path('/tmp/stability-spinner-owner-source-review-20260913-1'),
    }),
    ('stability-case-work-preparer-source-20260913-1', {
        'source': Path('/tmp/stability-case-work-preparer-review-20260913-f7gq8o9n'),
    }),
    ('stability-application-backend-map-source-20260913-1', {
        'source': Path('/tmp/stability-application-backend-map-20260913-_f9x_awt'),
    }),
]


def identity(path, label=None):
    data = path.read_bytes()
    return dict(path=str(path) if label is None else label, size=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def inventory(roots):
    result = []
    for label, root in roots.items():
        for path in [root] + sorted(root.rglob('*')):
            st = path.lstat()
            name = label if path == root else label + '/' + str(path.relative_to(root))
            row = dict(member=name, source=str(path), mode=stat.S_IMODE(st.st_mode))
            if stat.S_ISDIR(st.st_mode):
                row.update(kind='directory', size=0)
            else:
                assert stat.S_ISREG(st.st_mode), (path, 'nonregular source')
                row.update(kind='file', **{k: v for k, v in identity(path).items() if k != 'path'})
            result.append(row)
    assert len(result) <= 256 and sum(r['size'] for r in result) <= 16 * 1024**2
    assert len({r['member'] for r in result}) == len(result)
    return result


def archive(name, roots):
    rows = inventory(roots)
    path = REPO / 'docs/verification/evidence' / (name + '.tar.gz')
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                for row in rows:
                    info = tarfile.TarInfo(row['member'])
                    info.mode = row['mode']
                    info.mtime = 0
                    if row['kind'] == 'directory':
                        info.type = tarfile.DIRTYPE
                        tar.addfile(info)
                    else:
                        data = Path(row['source']).read_bytes()
                        assert len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256']
                        info.size = len(data)
                        tar.addfile(info, io.BytesIO(data))
    with tarfile.open(path, 'r:gz') as tar:
        members = tar.getmembers()
        assert len(members) == len(rows)
        for item, expected in zip(members, rows):
            assert item.name == expected['member'] and item.mode == expected['mode']
            assert item.uid == item.gid == item.mtime == 0
            if expected['kind'] == 'directory':
                assert item.isdir() and item.size == 0
            else:
                assert item.isfile() and item.size == expected['size']
                data = tar.extractfile(item).read()
                assert hashlib.sha256(data).hexdigest() == expected['sha256']
    assert inventory(roots) == rows, 'source changed during archival verification'
    manifest_path = REPO / 'docs/verification/evidence' / (name + '.members.json')
    manifest = dict(schema_version=1, kind='verified-source-archive-members',
                    archive=identity(path, str(path.relative_to(REPO))),
                    member_count=len(rows), regular_file_count=sum(r['kind'] == 'file' for r in rows),
                    content_bytes=sum(r['size'] for r in rows), members=rows,
                    every_archive_member_verified=True, source_rechecked_after_archive=True,
                    source_roots={k: str(v) for k, v in roots.items()})
    with manifest_path.open('x') as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return dict(archive=manifest['archive'], manifest=identity(manifest_path, str(manifest_path.relative_to(REPO))),
                member_count=manifest['member_count'], regular_file_count=manifest['regular_file_count'],
                content_bytes=manifest['content_bytes'])


record = dict(schema_version=1, kind='source-review-retention', status='RUNNING',
              scope='Source/review packaging and verification only; parent owns complete build and guest attempt archives.',
              helper=identity(Path(__file__)), archives=[], application_acceptance=False,
              transport_acceptance=False, production_gate_credit=False,
              test_execution=False, compiler_execution=False, guest_execution=False)
try:
    for name, roots in GROUPS:
        record['archives'].append(archive(name, roots))
        (CAPTURE / 'partial-record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    docs = ['stability-runnable-thread-payload-review-20260913.json',
            'stability-runnable-thread-payload-review-20260913.md',
            'stability-application-backend-map-20260913.json',
            'stability-application-backend-map-20260913.md']
    record['publications'] = [identity(REPO / 'docs/verification' / name, 'docs/verification/' + name) for name in docs]
    record.update(status='PASS_SOURCE_RETENTION_ONLY', original_sources_and_reviews_preserved=True,
                  all_members_verified=True, originals_unchanged=True)
    output = REPO / 'docs/verification/stability-payload-source-retention-20260913-1.json'
    with output.open('x') as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(identity(output, str(output.relative_to(REPO))), sort_keys=True))
    print(json.dumps(record['archives'], sort_keys=True))
except BaseException as error:
    record.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    raise
finally:
    (CAPTURE / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
