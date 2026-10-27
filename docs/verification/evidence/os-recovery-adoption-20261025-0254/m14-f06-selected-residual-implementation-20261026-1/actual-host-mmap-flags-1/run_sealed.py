"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute only this sealed finite ordinary HOST cohort, CPU6/job1 under Root grant.
"""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

D=Path(__file__).resolve().parent

def ref(path):
    p=Path(path)
    return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def verify(rows):
    for row in rows:
        if ref(row['path'])!=row:
            raise ValueError('sealed input/tool changed: '+row['path'])


def main():
    os.sched_setaffinity(0,{6})
    for kind,limit in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),
                       (resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:
        resource.setrlimit(kind,(limit,limit))
    manifest=json.loads((D/'SEALED-COMMANDS.json').read_text())
    assert manifest['configuration']['sha256']=='a74a4a7b3edef59a5db47c41e1056768540439002331aaaf158dd95e21c7888c'
    verify(manifest['inputs']+manifest['tools'])
    out=D/'output';out.mkdir(mode=0o700)
    results=[]
    for index,command in enumerate(manifest['commands']):
        verify(manifest['inputs']+manifest['tools'])
        started=time.monotonic()
        with (out/(str(index)+'.stdout')).open('xb') as stdout, (out/(str(index)+'.stderr')).open('xb') as stderr:
            child=subprocess.Popen(command['argv'],cwd=D,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                   start_new_session=True,close_fds=True,
                                   env={'PATH':'/usr/bin:/bin','LC_ALL':'C','RUST_BACKTRACE':'0'})
            deadline=started+90
            timed_out=False
            while True:
                pid,status,usage=os.wait4(child.pid,os.WNOHANG)
                if pid:break
                if time.monotonic()>=deadline:
                    timed_out=True
                    os.killpg(child.pid,signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid,signal.SIGKILL);child.wait()
                    raise RuntimeError('command timeout; own child joined: '+str(index))
                time.sleep(0.01)
            child.returncode=os.waitstatus_to_exitcode(status)
        try:
            os.killpg(child.pid,0)
            group_absent=False
        except ProcessLookupError:
            group_absent=True
        row=dict(index=index,argv=command['argv'],purpose=command['purpose'],pid=child.pid,
                 returncode=child.returncode,elapsed=time.monotonic()-started,CPU_user=usage.ru_utime,
                 CPU_system=usage.ru_stime,max_RSS_KiB=usage.ru_maxrss,direct_wait=True,
                 group_absent=group_absent,stdout=ref(out/(str(index)+'.stdout')),
                 stderr=ref(out/(str(index)+'.stderr')))
        results.append(row)
        (out/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',results=results),indent=2)+'\n')
        if child.returncode!=0 or not group_absent:
            raise RuntimeError('first command failure: '+str(index))
    names=['arch_mmap_supported_flags_bridge','arch_mmap_ignored_flags_bridge','arch_mmap_error_flags_bridge']
    def public_names(index):
        return [line.split()[-1] for line in (out/(str(index)+'.stdout')).read_text().splitlines() if line.split()]
    assert all(public_names(7).count(n)==1 for n in names)
    assert all(public_names(8).count(n)==0 for n in names)
    assert all(public_names(9).count(n)==1 for n in names)
    assert all(public_names(13).count(n)==1 for n in names)
    assert all(public_names(14).count(n)==1 for n in names)
    expected='PASS mmap flags original-C/provider parity masks3 classification36 ABI3\n'
    assert (out/'5.stdout').read_text()==expected
    assert (out/'6.stdout').read_text()==expected
    result=dict(status='PASS_F06_MMAP_FLAGS_ORDINARY_HOST',scope=__doc__,grant=manifest['grant'],
                sealed_manifest=ref(D/'SEALED-COMMANDS.json'),configuration=manifest['configuration'],
                results=results,checks={'genuine_NOCACHE_undefined':True,'Rust_providers_unique3':True,
                'selected_C_providers_absent3':True,'fallback_C_providers_present3':True,
                'selected_and_fallback_executable_provider_symbols_unique3':True,
                'original_C_Rust_masks3_classification36_ABI3':True,'fallback_same_parity':True},
                limits='HOST GCC9/Rust1.92 only; no GCC14/default image/native/whole-file retirement acceptance')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],commands=len(results),all_direct_waited=True,
                         all_groups_absent=True,CPU_seconds=sum(r['CPU_user']+r['CPU_system'] for r in results),
                         wall_seconds=sum(r['elapsed'] for r in results)),sort_keys=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        (D/'FIRST-FAILURE.json').write_text(json.dumps(dict(error=repr(error),scope=__doc__),indent=2)+'\n')
        raise
