"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-dispatched read-only Resource2 capture plus data binding; no native call.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parent;A=R

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def require_absent(paths):
 for p in paths:
  if os.path.lexists(p):raise FileExistsError(str(p))

def retain(argv,out,err):
 # Retain helper status stdout/stderr exclusively; helper owns final JSON.
 with out.open('xb') as stdout,err.open('xb') as stderr:
  child=subprocess.Popen(argv,stdout=stdout,stderr=stderr)
  rc=child.wait()
 return dict(argv=argv,pid=child.pid,direct_child_joined=True,returncode=rc,streams_closed=True,stdout=ref(out),stderr=ref(err))

def main():
 resource=R/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json';stderr=R/'RESOURCE-1-HELPER.stderr';stdout=R/'RESOURCE-1-HELPER.stdout'
 require_absent([resource,stdout,stderr,resource.with_name(resource.stem+'.PHYSICAL.stdout'),resource.with_name(resource.stem+'.PHYSICAL.stderr'),R/'RESOURCE-1-CAPTURE-JOIN.json',R/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json',R/'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json'])
 static=json.loads((R/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
 for source in static['capture_sources'].values():assert ref(Path(source['path']))==source
 publication=json.loads((R/'ACTUAL-STATIC-SOURCE-PUBLICATION.json').read_bytes())
 assert publication['status']=='PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS'
 for source in list(static['capture_sources'].values())+[ref(R/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json')]:assert source in publication['files']
 assert not list((A/'CAPTURE').iterdir()) and not list(Path(static['attempt_parent']).iterdir())
 assert not os.path.lexists(Path(static['attempt_parent'])/('attempt-'+static['nonce']))
 capture=retain(['/home/holden/anaconda3/bin/python3','-I','-B',str(R/'capture_fresh_f05_v2_resource.py'),'--output-path',str(resource)],stdout,stderr)
 if capture['returncode']==0:capture['resource']=ref(resource)
 with (R/'RESOURCE-1-CAPTURE-JOIN.json').open('x') as f:json.dump(capture,f,indent=2);f.write('\n')
 if capture['returncode']!=0:raise SystemExit(capture['returncode'])
 assert capture['stderr']['bytes']==0
 value=json.loads(resource.read_bytes());assert isinstance(value,dict) and len(value['observed_clocks'])==3
 # Data-only binder runs immediately after retained JSON; no model/source work
 # is required between fresh observation and a review-ready exact pending packet.
 bound=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(R/'bind_f05_v2_resource.py'),'--resource',str(resource)],check=False)
 raise SystemExit(bound.returncode)
if __name__=='__main__':main()
