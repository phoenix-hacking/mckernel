#!/usr/bin/env python3
"""Preserve complete fresh original-baseline captures; no new runtime launches."""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import gzip, hashlib, json, os, shutil, stat, subprocess, tarfile
assert os.getuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5}
work,repo=Path('/work'),Path('/workspace')
out=work/'stability-baseline-retained-20260913-1'
assert shutil.disk_usage(work).free > 3*1024**3
out.mkdir()
record=dict(schema_version=1,status='RUNNING',scope='Complete fresh original eight-suite replay evidence on retained module1/image3 only',started_utc=datetime.now(timezone.utc).isoformat(),captures=[],references=[],artifacts=[],native_compiler_bindings=[],guest_production_bindings=[],new_catalog_runtime_acceptance=False,transport_fault_runtime_verified=False,production_gate_credit=False)

def save():
    (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')

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
    record['helper']=identity(out/'helper.py')
    record['tree_verifier_source']=identity(work/'retain-native-ultra-final.py')
    selected=repo/'docs/verification/ultra-draft-inputs-20260909.json'
    inp=json.loads(selected.read_text())
    checkpoint=repo/inp['final_checkpoint']['path']
    assert identity(checkpoint)['sha256']==inp['final_checkpoint']['sha256']
    cp=json.loads(checkpoint.read_text())
    for group in ('native_compiler_bindings','guest_production_bindings'):
        for row in cp[group]:
            p=repo/row['path']; actual=identity(p)
            assert actual['sha256']==row['sha256'] and actual['size']==row['size'], str(p)
            record[group].append(row)
    for name in ('core','launcher','linux_kernel','mckernel_image','module_record','image_record'):
        row=inp['selected_pair'][name]
        assert identity(Path(row['path']))==row
    for row in inp['selected_pair']['modules']:
        assert identity(Path(row['path']))==row
    record['selected_pair']=inp['selected_pair']
    record['references']=[identity(selected),identity(checkpoint),identity(repo/'docs/verification/stability-bootstrap-20260913.json')]
    record['source_commit']=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,timeout=15).strip()
    names=['native-ultra-baseline-'+mode+'-guest-20260909-stability-20260913-1' for mode in ('memory','files','threads','signals')]+['native-ultra-control-regression-20260909-x86_64-stability-20260913-1','native-ultra-control-compat-20260909-i386-stability-20260913-1','native-ultra-signal-abi-guest-20260909-2026091301','native-ultra-futex-guest-20260909-2026091301','native-ultra-regression-batch-20260909-stability-20260913-1','stability-additional-baseline-20260913-1']
    for index,name in enumerate(names):
        capture=work/name
        child=json.loads((capture/'record.json').read_text())
        assert child['status']=='PASS',name
        if index<8:
            assert child['qemu_exit_code']==0,name
            assert child['qemu_args'][child['qemu_args'].index('-kernel')+1]==inp['selected_pair']['linux_kernel']['path']
        before=identity(capture/'record.json')
        archive=out/('stability-baseline-20260913-1-'+str(index+1).zfill(2)+'.tar.gz')
        print('ARCHIVE',name,flush=True)
        with archive.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as compressed:
                with tarfile.open(fileobj=compressed,mode='w') as tar:
                    tar.add(capture,arcname=capture.name)
        members=check_tree(capture,archive)
        assert identity(capture/'record.json')==before
        full=identity(archive)
        assert full['size']<95*1024**2,'archive needs additive ordered splitting: '+name
        publication=dict(full);publication['path']='docs/verification/evidence/'+archive.name
        record['captures'].append(dict(source=str(capture),record=before,status='PASS',full_capture=True,excludes=[],exact_tree_members=members,archive=publication,restore_parent='/work'))
        record['artifacts'].append(dict(source=full,published=publication))
        save()
    record.update(status='PASS',original_suites_passed=8,new_catalog_cases_accepted=0)
except BaseException as error:
    record.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    raise
finally:
    record['finished_utc']=datetime.now(timezone.utc).isoformat()
    save()
    print(record['status'],out,flush=True)
