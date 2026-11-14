#!/usr/bin/env python3
"""One fixed finite ordinary readback consumer; requires independent exact release.

Reuses the accepted ProcessProof v2 and capture descriptor identity contracts.
Selector read/cap algorithm follows native_rust_exact_disk_build_wrapper; its
kill branch is deliberately absent. Partial streams and uncertain identities stay.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import selectors
import stat
import subprocess
import time

BASE=Path(__file__).absolute().parent
SOURCE=BASE/'readback_capture.py'
TEST=BASE/'test_readback_capture.py'
PRODUCER=Path('/home/holden/mckernel-work/host-preparation/native-host-objtool-prelease-recovery-20261018-1/frozen/5-retirement_producer.py')
PRODUCER_SHA='760c2764a309481680c80afa30a90d3222a10efe78f14495c102a0415ea28699'
EVIDENCE=Path('/home/holden/mckernel-work/host-preparation/ihk-regular-owner-recovery-20261018-2/recover-evidence')
MEMBERS=('.',)
ARGV=('/usr/bin/sudo','-A','/usr/bin/tar','--format=pax','--one-file-system','-cf','-','-C',str(EVIDENCE),'--',*MEMBERS)
CAP=16<<20
TIMEOUT=30
CAPTURE=BASE/'capture-actual-1'

def need(ok,message):
    if not ok:raise ValueError(message)

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def new_file(parent,name):
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
    meta=os.fstat(fd)
    need(stat.S_ISREG(meta.st_mode) and (meta.st_uid,meta.st_gid,meta.st_nlink,stat.S_IMODE(meta.st_mode))==(1000,1000,1,0o600),'fresh UID1000 capture required')
    os.fsync(parent)
    return fd

def write_all(fd,raw):
    while raw:
        count=os.write(fd,raw);need(count>0,'write made no progress');raw=raw[count:]

def emit(parent,name,value):
    fd=new_file(parent,name)
    try:write_all(fd,canonical(value));os.fsync(fd)
    finally:os.close(fd)

class CaptureWriteError(ValueError):
    def __init__(self,written):
        super().__init__('capture write failed after approved partial chunk')
        self.written=written

def append_bounded(output,chunk,used,cap):
    need(used+len(chunk)<=cap,'CAPTURE_LIMIT_BEFORE_WRITE')
    remaining=memoryview(chunk);written=0
    try:
        while remaining:
            count=output.write(remaining)
            need(type(count) is int and 0<count<=len(remaining),'capture write made no progress')
            written+=count;remaining=remaining[count:]
    except BaseException as exc:
        raise CaptureWriteError(written) from exc
    return used+written

def stream_and_join(process,proof,outputs,cap=CAP,timeout=TIMEOUT,
                    selector_factory=selectors.DefaultSelector,reader=os.read,clock=time.monotonic):
    """Finite pipe drain and join, retaining partial bytes; never sends signals."""
    start=clock();used=0;sizes={'stdout':0,'stderr':0};failure=None
    direct_joined=False;code=None
    selector=selector_factory()
    try:
        for label,stream in (('stdout',process.stdout),('stderr',process.stderr)):
            os.set_blocking(stream.fileno(),False)
            selector.register(stream,selectors.EVENT_READ,label)
        while selector.get_map():
            proof.observe('waiting')
            remaining=timeout-(clock()-start)
            if remaining<=0:raise TimeoutError('READBACK_TIMEOUT')
            events=selector.select(remaining)
            for key,_ in events:
                chunk=reader(key.fd,min(65536,cap-used+1))
                if not chunk:
                    selector.unregister(key.fileobj);key.fileobj.close();continue
                try:used=append_bounded(outputs[key.data],chunk,used,cap)
                except CaptureWriteError as exc:
                    used+=exc.written;sizes[key.data]+=exc.written
                    raise
                sizes[key.data]+=len(chunk)
    except BaseException as exc:
        failure=dict(type=type(exc).__name__,message=str(exc)[:256])
    finally:
        # Close only this ordinary consumer's read endpoints; never signal or
        # remove anything. A producer may report EPIPE; such a result is HOLD.
        selector.close()
        for stream in (process.stdout,process.stderr):stream.close()
    try:
        code=process.wait(timeout=5)
        direct_joined=True
        proof.joined(code)
    except BaseException as exc:
        if failure is None:failure=dict(type=type(exc).__name__,message=str(exc)[:256])
    retired=direct_joined and proof.data.get('retirement_proven') is True
    success=failure is None and retired and code==0 and sizes['stderr']==0
    return dict(status='PASS_READBACK_CAPTURE' if success else 'HOLD_READBACK_CAPTURE',
                direct_child_joined=direct_joined,retirement_proven=retired,returncode=code,
                bytes=sizes,total_bytes=used,cap_bytes=cap,failure=failure,
                elapsed_seconds=clock()-start,signals_sent=False,partial_retained=True)

def load_producer():
    need(digest(PRODUCER)==PRODUCER_SHA,'accepted ProcessProof source drift')
    spec=importlib.util.spec_from_file_location('accepted_readback_process_proof',PRODUCER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def authorize(path,sha):
    need(path==BASE/'execution-release.json' and digest(path)==sha,'exact new release path/hash required')
    release=json.loads(path.read_bytes())
    need(release.get('status')=='PASS_EXACT_READBACK_EXECUTION_RELEASE' and release.get('author') and
         release.get('reviewer') and release['reviewer']!=release['author'] and
         release.get('execution_count')==1 and type(release['execution_count']) is int and
         release.get('argv')==list(ARGV) and release.get('source_sha256')==digest(SOURCE) and
         release.get('tests_sha256')==digest(TEST) and release.get('producer_sha256')==PRODUCER_SHA and
         release.get('capture_root')==str(CAPTURE) and release.get('cpu')==7 and
         release.get('cap_bytes')==CAP and release.get('timeout_seconds')==TIMEOUT and
         release.get('boot_id')==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and
         release.get('no_signals_no_cleanup') is True,'independent exact readback release required')
    return release

def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha256',required=True);a=p.parse_args()
    need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID1000 consumer required')
    need(os.sched_getaffinity(0)=={7},'exact CPU7 affinity required')
    resource.setrlimit(resource.RLIMIT_AS,(1<<30,1<<30));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))
    authorize(a.release,a.release_sha256)
    need(not os.path.lexists(CAPTURE),'fresh capture path required')
    os.mkdir(CAPTURE,0o700)
    parent=os.open(CAPTURE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    outputs={};process=proof=None
    try:
        for label,name in (('stdout','postflight.tar'),('stderr','tar.stderr')):
            outputs[label]=os.fdopen(new_file(parent,name),'wb',buffering=0)
        producer=load_producer();producer.enable_subreaper();before=producer.prepare_launch()
        process=subprocess.Popen(list(ARGV),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,start_new_session=True)
        proof=producer.ProcessProof(process,privileged_wrapper=True,pre_launch=before)
        emit(parent,'started.json',dict(argv=list(ARGV),pid=process.pid,identity=proof.data.get('identity'),prelaunch=before,signals_sent=False))
        result=stream_and_join(process,proof,outputs)
        for output in outputs.values():output.flush();os.fsync(output.fileno())
        emit(parent,'process-proof.json',proof.data)
        result.update(argv=list(ARGV),pid=process.pid,archive_sha256=digest(CAPTURE/'postflight.tar'),
                      application_acceptance=False,recovery_acceptance=False)
        emit(parent,'result.json',result)
        print(json.dumps(dict(status=result['status'],bytes=result['total_bytes'],retirement_proven=result['retirement_proven'])),flush=True)
        return 0 if result['status']=='PASS_READBACK_CAPTURE' else 1
    except BaseException as exc:
        emit(parent,'uncertain.json',dict(status='HOLD_READBACK_CAPTURE',pid=None if process is None else process.pid,
             identity=None if proof is None else proof.data.get('identity'),error=type(exc).__name__,signals_sent=False,partial_retained=True))
        raise
    finally:
        for output in outputs.values():output.close()
        os.close(parent)

if __name__=='__main__':raise SystemExit(main())
