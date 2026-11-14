from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import gzip,hashlib,json,os,shutil,stat,tarfile
assert os.getuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5}
work=Path('/work');out=work/'stability-permanent-collection-retained-20260913-1';out.mkdir()
assert shutil.disk_usage(work).free>3*1024**3
record=dict(schema_version=1,status='RUNNING',started_utc=datetime.now(timezone.utc).isoformat(),scope='Permanent guest2 native deadline/owner collection and physical comparison awaiting independent review; retain false polling-only ret_left flag discrepancy; actual C decoder84 infrastructure PASS, no catalog acceptance',artifacts=[],captures=[],new_catalog_acceptance=False,actual_transport_fault_verified=False,production_gate_credit=False)
def save():(out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
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
 shutil.copyfile(__file__,out/'helper.py');record['helper']=identity(out/'helper.py')
 names=['stability-transport-fault-run-20260913-permanent-backpressure-2', 'stability-transport-fault-guest-20260913-permanent-backpressure-2', 'stability-permanent-physical-comparison-20260913-1', 'stability-application-request-decoder-tests-20260913-1']
 for i,name in enumerate(names):
  source=work/name;child=json.loads((source/'record.json').read_text());before=identity(source/'record.json')
  assert child['status'] in ('PASS_ACTUAL_C_REQUEST_DECODER_INFRASTRUCTURE_ONLY','COLLECTED_REQUIRES_INDEPENDENT_FAULT_REVIEW','COLLECTED_REQUIRES_CONTRACT_REVIEW','PHYSICAL_COMPARISONS_MATCH_REQUIRES_INDEPENDENT_REVIEW','PHYSICAL_COMPARISONS_MATCH_ORIGINAL_RUN_FAIL','PASS_ACTUAL_LINUX_TERMINAL_BOUNDARY_ONLY','PASS_METADATA_PREFLIGHT_TESTS_ONLY','PASS_SYNTHETIC_PHYSICAL_COMPARATOR_ONLY','PASS_ACTUAL_RECEIVER_GATE_INFRASTRUCTURE_ONLY','PASS_BUILD_ONLY','FAIL','PASS','PREPARED_NOT_COMPILED_NOT_EXECUTED','SOURCE_EVIDENCE_WITH_PRESERVED_FAILURE','PASS_BUILD_AND_SYNTHETIC_COLLECTION_TESTS_ONLY','PASS_ACTUAL_C_PTY_INFRASTRUCTURE_ONLY','PASS_SYNTHETIC_FAULT_CONTROL_ONLY','PASS_PREPARED_NO_GUEST_EXECUTION','PREPARED_NOT_EXECUTED','PASS_PREFLIGHT_NO_GUEST_EXECUTION','PASS_SYNTHETIC_PHASE_PARSER_ONLY')
  archive=out/('stability-permanent-collection-20260913-1-'+str(i+1).zfill(2)+'.tar.gz')
  print('ARCHIVE',name,flush=True)
  with archive.open('xb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as compressed:
    with tarfile.open(fileobj=compressed,mode='w') as tar:tar.add(source,arcname=source.name)
  members=check_tree(source,archive);assert identity(source/'record.json')==before
  full=identity(archive);assert full['size']<95*1024**2
  publication=dict(full,path='docs/verification/evidence/'+archive.name)
  record['artifacts'].append(dict(source=full,published=publication))
  record['captures'].append(dict(source=str(source),record=before,status=child['status'],archive=publication,full_capture=True,excludes=[],exact_tree_members=members,restore_parent='/work'));save()
 record['status']='PASS'
except BaseException as error:record.update(status='FAIL',error_type=type(error).__name__,error=str(error));raise
finally:record['finished_utc']=datetime.now(timezone.utc).isoformat();save();print(record['status'],out,flush=True)
