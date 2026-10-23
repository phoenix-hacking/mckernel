import fcntl
import ast,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ENGINE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/matched-image-terminal-preparation-1/bound-matched-image-terminal-source-2/cleanup_pass_image.py')
EXPECTED='59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
def need(v,m):
 if not v:raise RuntimeError(m)
def run(a):
 p=subprocess.run(a,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
 if p.returncode or p.stderr or len(p.stdout)>4*1024**2:
  sys.stderr.write(json.dumps(dict(argv=a,returncode=p.returncode,stdout_bytes=len(p.stdout),stderr=p.stderr[:65536].decode('utf-8','replace'),stderr_total_bytes=len(p.stderr)))+'\n')
  raise RuntimeError('bounded read-only command')
 return p.stdout.decode()
need(os.geteuid()==0,'authenticated root read-only admission')
b=ENGINE.read_bytes();need(hashlib.sha256(b).hexdigest()==EXPECTED,'accepted census source')
code=next(ast.literal_eval(n.value) for n in ast.parse(b).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets))
pid=os.getpid();start=Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'retired-LONG-110f-final-physical-20261023-1',str(pid),start]))
need(proc['status']=='COMPLETE' and proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2,'complete publisher-free census')
bound_path=Path('/home/holden/mckernel-work/host-preparation/p12-long-normal-cancel-20261023-1/final-physical-preparation-1/ACTUAL-23-CLIENT-IDENTITIES.json');bound_raw=bound_path.read_bytes()
need(hashlib.sha256(bound_raw).hexdigest()=='1677a7b569d529485332d25b442940dc0e192162e68dd892baf018b058cc758f','exact authenticated23client binding')
facts=json.loads(bound_raw);need(len(facts['clients'])==23 and proc['boot_id']==facts['boot_id'],'exact23clients/currentboot')
identities=[facts['outer_anchor'],facts['inner_owner']]+facts['clients']
for identity in identities:
 need(not any(row[0]==identity['pid'] and str(row[2])==str(identity['proc_starttime']) for snapshot in proc['snapshots'] for row in snapshot),'retired exact owner/client identity remains in fresh completePROC')
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='CURRENT_RETIRED_LONG_COMPLETE_PROC_AND_23_CLIENT_OBSERVATION',proc=proc,bound_client_facts_sha256='1677a7b569d529485332d25b442940dc0e192162e68dd892baf018b058cc758f',exact_identities_checked=[dict(pid=x['pid'],proc_starttime=x['proc_starttime']) for x in identities],physical_clearance=False),sort_keys=True))
