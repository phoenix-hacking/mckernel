import fcntl,stat
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
proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'retired-LONG-5603-final-physical-20261023-1',str(pid),start]))
need(proc['status']=='COMPLETE' and proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2,'complete publisher-free census')
bound_path=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/next-live-observation-5603-1/physical-preparation-1/ACTUAL-23-CLIENT-IDENTITIES.json');bound_raw=bound_path.read_bytes()
need(hashlib.sha256(bound_raw).hexdigest()=='6af858f21a34eb2c2d5fe8b3264ec7fa39bc38a885067b2f4967dd2531ca0ae7','exact authenticated23client binding')
facts=json.loads(bound_raw);need(len(facts['clients'])==23 and proc['boot_id']==facts['boot_id'],'exact23clients/currentboot')
# One bounded retained directory listing supplies exact command-ledger completeness.
root=Path(facts['owner_evidence_root']);root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
try:
 before=os.fstat(root_fd);directory_names=sorted(os.listdir(root_fd));after=os.fstat(root_fd);named=root.lstat()
 fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_mtime_ns','st_ctime_ns')
 need(stat.S_ISDIR(before.st_mode) and before.st_uid==before.st_gid==0 and stat.S_IMODE(before.st_mode)==0o700 and len(directory_names)<=4096 and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields),'bounded stable retained owner directory')
 need(before.st_dev==facts['owner_evidence_root_identity']['dev'] and before.st_ino==facts['owner_evidence_root_identity']['inode'],'exact authenticated retained owner directory identity')
 command_names=sorted(name for name in directory_names if name.endswith('.json') and name.partition('-')[0].isdigit())
 need(command_names==sorted(row['name'] for row in facts['clients']),'complete exact23command client ledger; additional or missing command identity')
finally:os.close(root_fd)
identities=[facts['outer_anchor'],facts['inner_owner']]+facts['clients']
for identity in identities:
 need(not any(row[0]==identity['pid'] and str(row[2])==str(identity['proc_starttime']) for snapshot in proc['snapshots'] for row in snapshot),'retired exact owner/client identity remains in fresh completePROC')
for observed_pid in facts['container_init_observation']['positive_retained_pids']:
 need(not any(row[0]==observed_pid for snapshot in proc['snapshots'] for row in snapshot),'observed containerinit PID with unknownbirth remains in fresh completePROC')
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='CURRENT_RETIRED_LONG_COMPLETE_PROC_AND_23_CLIENT_OBSERVATION',proc=proc,bound_client_facts_sha256='6af858f21a34eb2c2d5fe8b3264ec7fa39bc38a885067b2f4967dd2531ca0ae7',exact_identities_checked=[dict(pid=x['pid'],proc_starttime=x['proc_starttime']) for x in identities],observed_container_init_PID_absence_checked=facts['container_init_observation']['positive_retained_pids'],container_init_birth=None,retained_owner_directory_listing=directory_names,exact_command_names=command_names,retained_owner_directory_identity={'dev':before.st_dev,'inode':before.st_ino},physical_clearance=False),sort_keys=True))
