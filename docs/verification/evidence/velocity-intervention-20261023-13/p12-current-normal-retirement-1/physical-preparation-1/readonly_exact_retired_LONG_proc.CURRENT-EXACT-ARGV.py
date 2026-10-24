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
bound_path=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/p12-current-normal-retirement-1/physical-preparation-1/ACTUAL-23-CLIENT-IDENTITIES.json');bound_raw=bound_path.read_bytes()
need(hashlib.sha256(bound_raw).hexdigest()=='d866561e54d713e3894f19ac7e85485bef65d2df9fc5f544872bbd246a1a9f3f','exact authenticated current23client binding')
facts=json.loads(bound_raw)
need(len(facts['clients'])==23 and facts['outer_anchor'] is None and facts['outer_sudo'] is None and facts['outer_anchor_gap']=='Root original capture log explicitly retained no controller/sudo birth identity; no guessed or prior-owner anchors substituted.','explicit current historical-anchor gap, never generic skip-NULL')
need(facts['inner_owner']=={'pid':4056308,'proc_starttime':60669407},'exact current known owner birth')
current_raw=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/p12-current-normal-retirement-1/physical-preparation-1/CURRENT-EXACT-ARGV-AND-TERMINAL-BINDINGS.json').read_bytes();need(hashlib.sha256(current_raw).hexdigest()=='0644ffb4d65f96f784ccd7de6750f842284eda3532e72971f974a7479c31cb67','exact current argv/controlchain/terminal binding')
current=json.loads(current_raw)
need(current['facts']['sha256']=='d866561e54d713e3894f19ac7e85485bef65d2df9fc5f544872bbd246a1a9f3f' and current['parent_terminal_tool_session']==25780 and current['parent_terminal_returncode']==1 and current['missing_historical_controller_sudo_births'] is True and current['known_identity_count']==24,'exact alternate current observation authority')
for source in current['source_bindings']:
 need(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256'],'current source/request argv token pin')
auth=current['root_authenticated_current_closed_facts'];auth_raw=Path(auth['path']).read_bytes()
need(hashlib.sha256(auth_raw).hexdigest()==auth['sha256'],'actual root closed evidence authority')
auth=json.loads(auth_raw)
need(auth['exported_bytes_validated'] is True and auth['authenticated_request_sha256']==facts['actual_outer_closed_receipt']['request']['sha256'] and auth['capture']==facts['actual_outer_closed_receipt']['capture'] and auth['owner_result']==facts['normal_owner_result'],'current request/streams/started/owner joins bound')
needle='def publisher(exe,argv):\n'
need(code.count(needle)==1,'one accepted publisher predicate insertion site')
addition='CURRENT_EXACT_TOKENS='+repr(tuple(current['current_exact_tokens']))+'\n'+needle+'    if any(arg in CURRENT_EXACT_TOKENS for arg in argv): return True\n'
code=code.replace(needle,addition)
pid=os.getpid();start=Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'retired-LONG-4a76457e-current-exact-argv-physical-20261024-1',str(pid),start]))
need(proc['status']=='COMPLETE' and proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2,'complete strengthened publisher-free census')
need(proc['boot_id']==facts['boot_id'],'currentboot')
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
identities=[facts['inner_owner']]+facts['clients']
for identity in identities:
 need(not any(row[0]==identity['pid'] and str(row[2])==str(identity['proc_starttime']) for snapshot in proc['snapshots'] for row in snapshot),'retired exact owner/client identity remains in fresh completePROC')
for observed_pid in facts['container_init_observation']['positive_retained_pids']:
 need(not any(row[0]==observed_pid for snapshot in proc['snapshots'] for row in snapshot),'observed containerinit PID with unknownbirth remains in fresh completePROC')
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='CURRENT_RETIRED_LONG_EXACT_ARGV_AND_24_KNOWN_IDENTITIES_OBSERVATION',proc=proc,bound_client_facts_sha256='d866561e54d713e3894f19ac7e85485bef65d2df9fc5f544872bbd246a1a9f3f',current_exact_tokens=current['current_exact_tokens'],current_controlchain_binding_sha256='0644ffb4d65f96f784ccd7de6750f842284eda3532e72971f974a7479c31cb67',missing_historical_controller_sudo_births=True,unknown_historical_PID_absence_claim=False,exact_identities_checked=[dict(pid=x['pid'],proc_starttime=x['proc_starttime']) for x in identities],observed_container_init_PID_absence_checked=facts['container_init_observation']['positive_retained_pids'],container_init_birth=None,retained_owner_directory_listing=directory_names,exact_command_names=command_names,retained_owner_directory_identity={'dev':before.st_dev,'inode':before.st_ino},physical_clearance=False),sort_keys=True))
