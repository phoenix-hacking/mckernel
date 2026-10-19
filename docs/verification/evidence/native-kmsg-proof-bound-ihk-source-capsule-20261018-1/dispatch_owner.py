#!/usr/bin/env python3
"""One ordinary owner dispatch, preserving streams/join; no timeout on lock owner."""
import argparse,hashlib,json,os,resource,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent
OWNER=E/'capsule/scripts/native_running_external_modules_owner.py'
OWNER_SHA='349d503862eb333151050d973138dae559652b7a5dc47bc52e06fe7ce14ffa5f'
CAP=32*1024**2
SUCCESS_METADATA_CAP=512*1024

def need(ok,s):
    if not ok:raise ValueError(s)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dispatch(request,request_sha,release,release_sha,output):
    need(sha(OWNER)==OWNER_SHA and sha(request)==request_sha and sha(release)==release_sha,'exact source/request/release')
    need(output.is_absolute() and output.parent.resolve()==output.parent and not output.exists(),'fresh dispatch root');output.mkdir(mode=0o700)
    argv=['/home/holden/anaconda3/bin/python3','-B',str(OWNER),'--request',str(request),'--request-sha256',request_sha,'--release',str(release),'--release-sha256',release_sha]
    def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic()
    with (output/'owner.stdout').open('xb') as out,(output/'owner.stderr').open('xb') as err:
        p=subprocess.Popen(argv,stdout=out,stderr=err,stdin=subprocess.DEVNULL,start_new_session=True,preexec_fn=cap)
        p.wait() # The inner probe has35+2wall; never interrupt an owner cleaning locks.
    absent=False
    try:os.killpg(p.pid,0)
    except ProcessLookupError:absent=True
    captures={}
    for role in ('stdout','stderr'):
        f=output/('owner.'+role);need(f.stat().st_size<=CAP,'capture cap');captures[role]=dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f))
    row=dict(argv=argv,pid=p.pid,returncode=p.returncode,direct_child_joined=True,owned_group_absent=absent,seconds=time.monotonic()-start,request=dict(path=str(request),sha256=request_sha),release=dict(path=str(release),sha256=release_sha),owner_sha256=OWNER_SHA,captures=captures)
    with (output/'dispatch.status.json').open('x') as f:json.dump(row,f,indent=2);f.write('\n')
    need(p.returncode==0 and absent and all(r['bytes']<=SUCCESS_METADATA_CAP for r in captures.values()),'owner failed/group retirement/capture uncertainty; preserve streams/status');return row

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('request','release','output'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('request-sha256','release-sha256'):p.add_argument('--'+n,required=True)
    a=p.parse_args();r=dispatch(a.request,a.request_sha256,a.release,a.release_sha256,a.output);print(json.dumps({'returncode':r['returncode'],'direct_child_joined':r['direct_child_joined']}))
if __name__=='__main__':main()
