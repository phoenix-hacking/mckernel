"""Bounded source-only current68 copy; no SDK/compiler/root/runtime operations."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,'/home/holden/mckernel')
from scripts import native_running_external_modules_offline as driver
from scripts import native_running_external_modules_owner as owner
OUT=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel')
PREP=REPO/'docs/verification/evidence/current68-host-control-sdk-preparation-20261022-1.json'
FIELDS=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def nine(meta):return {field:getattr(meta,field) for field in FIELDS}
def stable_read(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        assert stat.S_ISREG(before.st_mode), 'source must be regular'
        chunks=[];total=0
        while True:
            raw=os.read(fd,65536)
            if not raw:break
            total+=len(raw)
            assert total<=8*1024**2,'source growth cap'
            chunks.append(raw)
        after=os.fstat(fd);linked=path.lstat()
        assert nine(before)==nine(after)==nine(linked),'regular-FD identity changed'
        raw=b''.join(chunks)
        assert len(raw)==before.st_size,'source read length'
        return raw,nine(before)
    finally:os.close(fd)
manifest=driver.load_preparation(PREP)
owner.validate_preparation(manifest)
modules=OUT/'source-modules';modules.mkdir()
rows=[];total=0
with (OUT/'copy-rows.jsonl').open('x') as progress:
    for row in manifest['closure']:
        relative=Path(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and str(relative)==row['path']
        raw,source_identity=stable_read(Path(row['origin']))
        digest=hashlib.sha256(raw).hexdigest()
        assert (digest,len(raw))==(row['sha256'],row['bytes']), 'current source origin sha/bytes mismatch: '+row['path']
        total+=len(raw);assert total<=8*1024**2,'aggregate source growth cap'
        target=modules/relative;target.parent.mkdir(parents=True,exist_ok=True)
        mode=stat.S_IMODE(source_identity['st_mode'])
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode)
        try:
            os.fchmod(fd,mode)
            view=memoryview(raw)
            while view:
                written=os.write(fd,view);assert written>0;view=view[written:]
            os.fsync(fd)
        finally:os.close(fd)
        copied,destination_identity=stable_read(target)
        assert copied==raw and hashlib.sha256(copied).hexdigest()==row['sha256']
        assert stat.S_IMODE(destination_identity['st_mode'])==mode,'copied mode mismatch'
        assert destination_identity['st_nlink']==1,'bundle alias must be distinct file'
        observed=dict(path=row['path'],origin=row['origin'],sha256=digest,bytes=len(raw),
                      permission_mode_octal=oct(mode),source_fd9=source_identity,bundle_fd9=destination_identity)
        rows.append(observed);progress.write(json.dumps(observed,sort_keys=True)+'\n');progress.flush()
actual={str(p.relative_to(modules)) for p in modules.rglob('*') if p.is_file()}
assert actual=={r['path'] for r in manifest['closure']}
source_map={r['path']:[r['sha256'],r['bytes']] for r in rows}
assert source_map==driver.EXACT_SOURCE_MAP==owner.EXACT_SOURCE_MAP
identity_rows=[[r['path'],r['sha256'],r['bytes']] for r in sorted(rows,key=lambda r:r['path'])]
identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
assert identity==manifest['source_identity'] and len(rows)==68 and total==1346042
aliases={r['path']:r for r in rows if r['path'] in ('mcctrl.rs','mcctrl_rust.rs')}
assert aliases['mcctrl.rs']['sha256']==aliases['mcctrl_rust.rs']['sha256']
assert aliases['mcctrl.rs']['bundle_fd9']['st_ino']!=aliases['mcctrl_rust.rs']['bundle_fd9']['st_ino']
value=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 status='PASS_EXACT68_SOURCE_BUNDLE_ONLY',preparation=dict(path=str(PREP),sha256=driver.digest(PREP)),
 source_files=len(rows),source_bytes=total,source_identity=identity,source_identity_encoding='SHA256 compact JSON sorted [relative,sha256,bytes] triples',
 exact_source_map=source_map,fd9_fields=list(FIELDS),rows=rows,alias_paths=list(aliases),
 references_not_copied=manifest['references'],reference_count=len(manifest['references']),
 installed_manifest_checks=['driver.load_preparation(actual frozen current68)','owner.validate_preparation(actual frozen current68)'],
 sourcebundle_only=True,actual_SDK=None,actual_modules=None,execution_release=None,module_acceptance=False,native_acceptance=False,rust_retirement=False)
(OUT/'source-bundle-manifest.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:value[k] for k in ('status','source_files','source_bytes','source_identity','reference_count','actual_SDK','actual_modules','execution_release')},indent=2))
