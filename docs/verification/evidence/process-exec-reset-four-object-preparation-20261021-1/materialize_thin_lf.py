"""Preparation proposal: private byte copies, never hardlinks or Git mutation.

Not invoked by this preparation. Final source validation is mandatory and
failures preserve the entire new source tree and journal for review.
"""
from pathlib import Path
import hashlib
import json
import os
import stat
import sys
sys.path.insert(0,'/home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/locking-correction-1/compiler-owner-preparation-1')
from thin_source_contract_lf import validate_thin_document,validate_thin_source,BASE_CANDIDATE,BASE_IHK,BASE_ROOT
from thin_source_contract_lf import _thin_check_tracked_link

HERE=Path('/home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/locking-correction-1/compiler-owner-preparation-1')
OUTPUT_ROOT=Path(__file__).resolve().parent
DESTINATION=OUTPUT_ROOT/'materialized-source'
OVERLAYS={'kernel/rust/syscall_policy.rs':Path('/home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/locking-correction-1/compiler-owner-preparation-1/syscall_policy.rs'),'kernel/syscall.c':Path('/home/holden/mckernel-work/host-preparation/process-owned-fork-rust-next-preparation-20261021-1/locking-correction-1/compiler-owner-preparation-1/syscall.c'),'.compiler-generated/config.h':Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/full-image-attempt-1/owner-work/output/build/config.h')}
BASE_ROOT='/home/holden/mckernel-work/host-preparation/numa-vm-policy-insert-rust-20261021-1/production-object-preparation-1/materialized-source'


def main():
    document=json.loads((HERE/'thin-inputs.canonical-lf.json').read_text())
    files,metadata=validate_thin_document(document,BASE_CANDIDATE,BASE_IHK)
    expected=dict(files);expected.update({p:row['sha256'] for p,row in metadata.items()})
    assert not DESTINATION.exists() and not DESTINATION.is_symlink()
    assert HERE.resolve()==HERE
    DESTINATION.mkdir(mode=0o700)
    for relative in document['gitlinks']:
        if relative!='ihk':
            (DESTINATION/relative).mkdir(parents=True,exist_ok=True)
    journal=OUTPUT_ROOT/'materialization-journal.jsonl'
    with journal.open('x') as log:
        for relative,digest in sorted(expected.items()):
            source=OVERLAYS.get(relative, Path(BASE_ROOT)/relative)
            if relative in document['materialized_symlinks']:
                row=document['materialized_symlinks'][relative]
                actual,size=_thin_check_tracked_link(Path(BASE_ROOT),source,row)
                assert actual==digest
                for measure,floor in [(Path('/home/holden'),16*2**30),(HERE,12*2**30)]:
                    fs=os.statvfs(measure)
                    assert fs.f_bavail*fs.f_frsize>=floor+size+512*2**20, 'disk floor/headroom'
                destination=DESTINATION/relative;destination.parent.mkdir(parents=True,exist_ok=True)
                destination.symlink_to(row['target'])
                # Preserve raw link bytes; never open/chmod through a link.
                log.write(json.dumps({'path':relative,'sha256':actual,'size':size,
                                      'kind':'symlink','target':row['target']})+'\n')
                log.flush()
                continue
            assert source.resolve()==source and stat.S_ISREG(source.lstat().st_mode)
            for measure,floor in [(Path('/home/holden'),16*2**30),(HERE,12*2**30)]:
                fs=os.statvfs(measure)
                assert fs.f_bavail*fs.f_frsize>=floor+source.stat().st_size+512*2**20, 'disk floor/headroom'
            destination=DESTINATION/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256()
            with source.open('rb') as inp,destination.open('xb') as out:
                for block in iter(lambda:inp.read(1024*1024),b''):
                    h.update(block);out.write(block)
                out.flush();os.fsync(out.fileno())
            assert h.hexdigest()==digest,relative
            destination.chmod(document['materialized_modes'][relative])
            log.write(json.dumps({'path':relative,'sha256':digest,'size':destination.stat().st_size})+'\n')
            log.flush()
        observed=validate_thin_source(DESTINATION,document,BASE_CANDIDATE,BASE_IHK)
        receipt=json.dumps({
            'status':'PASS_SOURCE_MATERIALIZATION_ONLY','source':str(DESTINATION),
            'source_derivative_sha256':observed['source_derivative_sha256'],
            'materialization_sha256':observed['materialization_sha256'],
            'source_entries':len(expected),'regular_files':len(expected)-len(document['materialized_symlinks']),
            'tracked_symlinks':len(document['materialized_symlinks']),
            'builds':0,'guests':0},indent=2)+'\n'
        with (OUTPUT_ROOT/'materialization-receipt.json').open('x') as output:
            output.write(receipt);output.flush();os.fsync(output.fileno())


    # Existing four-object consumer manifest schema; emit only regular rows.
    # Tracked symlinks remain authenticated by the unchanged thin validator.
    rows=[]
    for relative,digest in sorted(expected.items()):
        if relative in document['materialized_symlinks']:
            continue
        destination=DESTINATION/relative
        rows.append(dict(relative=relative,origin=str(destination),bytes=destination.stat().st_size,sha256=digest))
    source_manifest=dict(schema='mckernel.current-guest-phase4-source-manifest.v1',
        status='SOURCE_MATERIALIZED_ONLY',source_identity=observed['materialization_sha256'],
        count=len(rows),rows=rows,atime_excluded=True,
        source_state=dict(source_derivative_sha256=observed['source_derivative_sha256'],
            materialization_sha256=observed['materialization_sha256'],tracked_symlinks=len(document['materialized_symlinks']),
            thin_document_sha256=hashlib.sha256((HERE/'thin-inputs.canonical-lf.json').read_bytes()).hexdigest()))
    with (OUTPUT_ROOT/'source-manifest.json').open('x') as output:
        json.dump(source_manifest,output,sort_keys=True,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
    # Same private work-root creation as the qualified phase4 materializer.
    work=OUTPUT_ROOT/'work';work.mkdir(mode=0o700)
    for name in ('output','home','tmp'):
        (work/name).mkdir(mode=0o700)


if __name__=='__main__':
    assert Path('/').is_relative_to(Path('/')), 'required accepted Python Path API'
    print(json.dumps({'interpreter':sys.executable,'version':sys.version,'required_Path_API':True}),flush=True)
    main()
