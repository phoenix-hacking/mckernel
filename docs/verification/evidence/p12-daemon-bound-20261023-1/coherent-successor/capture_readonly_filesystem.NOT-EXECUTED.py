"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact proposed read-only root query, using the unchanged accepted owned_capture.
No Docker workload, build, guest, daemon configuration or runtime release.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys

D=Path(__file__).resolve().parent
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
REQUEST=D/'ROOT-READONLY-CAPTURE-REQUEST.NOT-RELEASED.json'

def need(ok,message):
    if not ok:raise RuntimeError(message)

def main():
    need(len(sys.argv)==2 and len(sys.argv[1])==64,'exact request digest argument')
    need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary parent identity')
    need(os.sched_getaffinity(0)=={7},'exact parentCPU7')
    for kind,pair in [(resource.RLIMIT_AS,(2*2**30,)*2),(resource.RLIMIT_CPU,(30,30)),
                      (resource.RLIMIT_FSIZE,(8*2**20,)*2),(resource.RLIMIT_CORE,(0,0)),
                      (resource.RLIMIT_NOFILE,(256,256))]:
        need(resource.getrlimit(kind)==pair,'exact parent readonly capture profile')
    need(hashlib.sha256(HELPER.read_bytes()).hexdigest()==HELPER_SHA,'accepted capture helper drift')
    spec=importlib.util.spec_from_file_location('accepted_readonly_capture',HELPER)
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    h.hashed(REQUEST,65536)
    raw=REQUEST.read_bytes();need(hashlib.sha256(raw).hexdigest()==sys.argv[1],'exact readonly request digest')
    request=json.loads(raw)
    need(request['schema']=='mckernel.p12.readonly-filesystem-capture.v1','exact request schema')
    selfpin=h.hashed(Path(__file__).resolve(),65536)
    need(selfpin['sha256']==request['wrapper_sha256'],'exact capture wrapper source')
    query=request['query'];pin=h.hashed(Path(query['path']),65536)
    need(pin['sha256']==query['sha256'],'exact readonly query source')
    need(request['wall_seconds']==35,'exact readonly wall deadline')
    rootargv=request['root_argv']
    need(rootargv==['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit',
                   '--as=2147483648:2147483648','--cpu=30:30','--fsize=8388608:8388608',
                   '--core=0:0','--nofile=256:256','--','/usr/bin/python3','-I','-B',
                   query['path'],query['sha256']], 'exact read-only root argv')
    capture=Path(request['capture_directory'])
    need(capture==D/'actual-readonly-filesystem-capture-2','exact capture retention path')
    capture.mkdir(mode=0o700)
    h.write(capture/'command.json',dict(scope=__doc__.splitlines()[0],argv=rootargv,
             helper_sha256=HELPER_SHA,query=query,request_sha256=sys.argv[1],wall_seconds=35,
             inherited_limits='exact parent profile; root prlimit repeats it; limits callback is no-op'))
    result=h.owned_capture(dict(argv=rootargv),capture,35,lambda:None)
    h.write(capture/'CAPTURE-RESULT.json',result)
    need(result['returncode']==0 and result['direct_child_joined'] is True and
         result['group_absent'] is True and result['closed_streams'] is True and
         result['error'] is None and result['retirement_error'] is None and
         result['unexpected_group_members']==[] and result['remaining_group_members']==[],
         'exact readonly capture failed or retirement uncertain')
    need(result['captures']['stderr']['size']==0 and
         result['captures']['stdout']['size']<=16384,'exact readonly capture stream shape')
    observation=json.loads((capture/'stdout').read_bytes())
    need(observation['mutations']==0 and observation['workloads']==0,'readonly result scope')
    h.write(capture/'CLOSED-QUERY-RESULT.json',dict(status='PASS_READONLY_FACTS_ONLY',
            query=query,observed=observation,physical_allocation_bound=False,native_acceptance=False))
    print('PASS closed read-only daemon filesystem facts; no allocation or runtime acceptance')

if __name__=='__main__':main()
