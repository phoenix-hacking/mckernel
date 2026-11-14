import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile

REPO = Path('/home/holden/mckernel')
CAPTURE = Path('/tmp/stability-preflight-source-retention-20260913-hk6b8vub')
GROUPS = [('stability-application-preflight-source-20260913-1', {'source': Path('/tmp/stability-application-preflight-source-20260913-5refja9x')})]


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
    docs = ['stability-application-preflight-review-20260913.json']
    record['publications'] = [identity(REPO / 'docs/verification' / name, 'docs/verification/' + name) for name in docs]
    inspection = Path('/tmp/stability-application-preflight-source-20260913-5refja9x/pinned-review/inspection.json')
    record['pinned_evidence_inspection'] = identity(inspection)
    record['pinned_test_result'] = dict(status='PASS_METADATA_PREFLIGHT_TESTS_ONLY', cases=12, raw_wait_status=0, original_reports=23, retained_artifact_hash_checks=339, reviewer_did_not_rerun=True, parent_full_attempt_archive_separate=True)
    record.update(status='PASS_METADATA_TEST_SOURCE_RETENTION_ONLY', original_sources_and_reviews_preserved=True,
                  all_members_verified=True, originals_unchanged=True)
    output = REPO / 'docs/verification/stability-application-preflight-tests-review-20260913-1.json'
    with output.open('x') as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(identity(output, str(output.relative_to(REPO))), sort_keys=True))
    print(json.dumps(record['archives'], sort_keys=True))
except BaseException as error:
    record.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    raise
finally:
    (CAPTURE / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
