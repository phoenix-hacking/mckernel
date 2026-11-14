from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import gzip, hashlib, json, os, shutil, stat, tarfile
assert os.getuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5}
work=Path('/work');out=work/'stability-review-retained-20260913-2';out.mkdir()
record=dict(status='RUNNING',artifacts=[],captures=[],started_utc=datetime.now(timezone.utc).isoformat(),scope='Reviewed fixture compilation and preserved source-stage/harness failures; no guest fault or new catalog runtime evidence',new_catalog_acceptance=False,production_gate_credit=False)
def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return dict(path=str(path), size=path.stat().st_size, sha256=digest.hexdigest())

def check_tree(source, path):
    """Read every archived byte and check the exact live tree, modes and links."""
    seen = set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            assert parts and parts[0] == source.name and '..' not in parts
            relative = str(PurePosixPath(*parts[1:]))
            assert relative not in seen, (source, relative)
            seen.add(relative)
            current = source / relative
            info = current.lstat()
            assert stat.S_IMODE(info.st_mode) == stat.S_IMODE(member.mode), (source, relative)
            if member.isdir():
                assert stat.S_ISDIR(info.st_mode)
            elif member.issym():
                assert stat.S_ISLNK(info.st_mode) and os.readlink(current) == member.linkname
            elif member.isfifo():
                assert stat.S_ISFIFO(info.st_mode)
            elif member.ischr() or member.isblk():
                assert (member.ischr() and stat.S_ISCHR(info.st_mode)) or (member.isblk() and stat.S_ISBLK(info.st_mode))
                assert (member.devmajor, member.devminor) == (os.major(info.st_rdev), os.minor(info.st_rdev))
            else:
                assert stat.S_ISREG(info.st_mode) and (member.isfile() or member.islnk()), (source, relative)
                digest, size = hashlib.sha256(), 0
                with archive.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b''):
                        size += len(chunk)
                        digest.update(chunk)
                actual = identity(current)
                assert (size, digest.hexdigest()) == (actual['size'], actual['sha256']), (source, relative)
    expected = {'.'}
    for parent, dirs, files in os.walk(source, followlinks=False):
        expected.update(str((Path(parent) / name).relative_to(source)) for name in dirs + files)
    assert seen == expected, (source, sorted(expected - seen)[:10], sorted(seen - expected)[:10])
    return len(seen)
try:
    shutil.copyfile(__file__,out/'helper.py')
    names=['stability-service-failure-tests-20260913-2','stability-service-failure-stage-20260913-3','stability-service-failure-tests-20260913-3']
    for i,name in enumerate(names):
        source=work/name; child=json.loads((source/'record.json').read_text())
        assert child['status']==['FAIL','STAGED_NOT_RUN','PASS'][i]
        archive=out/('stability-review-20260913-2-'+str(i+1).zfill(2)+'.tar.gz')
        print('ARCHIVE',name,flush=True)
        with archive.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as compressed:
                with tarfile.open(fileobj=compressed,mode='w') as tar:tar.add(source,arcname=source.name)
        members=check_tree(source,archive);full=identity(archive);assert full['size']<95*1024**2
        publication=dict(full);publication['path']='docs/verification/evidence/'+archive.name
        record['artifacts'].append(dict(source=full,published=publication))
        record['captures'].append(dict(source=str(source),record=identity(source/'record.json'),status=child['status'],archive=publication,full_capture=True,excludes=[],exact_tree_members=members,restore_parent='/work'))
    record['status']='PASS'
except BaseException as error:record.update(status='FAIL',error=str(error));raise
finally:
    record['finished_utc']=datetime.now(timezone.utc).isoformat()
    (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(record['status'],out,flush=True)
