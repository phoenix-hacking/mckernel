"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Own one exact independent finite verifier and retain its positive direct join.
No timeout, signals, restart, capture, holder, Docker or producer operation.
"""
from pathlib import Path
import json
import os
import resource
import subprocess
import sys

OWN = Path(__file__).resolve().parent
sys.path.insert(0,str(OWN))
from check_static import ref, load

def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def birth(pid):
    return int(Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19])

def profile():
    os.sched_setaffinity(0,{0})
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))

def main():
    release = load(OWN/'EXECUTION-RELEASE.json')
    assert release['decision'] == 'PASS_EXACT_BFD_FINITE_CAPTURE_HOLDER_AND_CONDITIONAL_BUILD_RELEASE'
    assert ref(OWN/'EXECUTION-RELEASE.json')['sha256'] == 'c2f89ff33a2e3cc8cfa4df7fa4ae978154bb1c0be96cf87697a7678b8dfa3159'
    argv = release['commands'][0]['argv']
    assert release['commands'][0]['owner'] == '/root/observerreview'
    assert os.getuid() == os.geteuid() == 1000
    write(OWN/'FINITE-ONCE-CLAIM.json',dict(scope=__doc__.splitlines()[0],reviewer='/root/observerreview',argv=argv,release=ref(OWN/'EXECUTION-RELEASE.json')))
    with (OWN/'finite.stdout').open('xb') as out,(OWN/'finite.stderr').open('xb') as err:
        child = subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True,preexec_fn=profile)
        child_birth = birth(child.pid)
        write(OWN/'FINITE-STARTED.json',dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=child_birth,argv=argv,affinity=sorted(os.sched_getaffinity(child.pid)),AS_bytes=2<<30,release=ref(OWN/'EXECUTION-RELEASE.json')))
        print(json.dumps(dict(status='FINITE_STARTED',pid=child.pid,starttime=child_birth)),flush=True)
        code = child.wait()
    members=[];errors=[]
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():continue
        try:
            fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2]) == child.pid:members.append(dict(pid=int(directory.name),state=fields[0],group=int(fields[2])))
        except (FileNotFoundError,ProcessLookupError):pass
        except BaseException as error:errors.append(dict(pid=directory.name,error=repr(error)))
    value=dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=child_birth,returncode=code,
        positive_direct_wait_join=True,streams_closed=True,remaining_group_members=members,
        group_observation_errors=errors,process_group_absent=not members and not errors,
        stdout=ref(OWN/'finite.stdout'),stderr=ref(OWN/'finite.stderr'),automatic_retry=False)
    write(OWN/'FINITE-JOINED.json',value)
    print(json.dumps(value),flush=True)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
