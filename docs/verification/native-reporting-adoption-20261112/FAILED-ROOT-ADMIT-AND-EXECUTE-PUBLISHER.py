import datetime,hashlib,json,os,pathlib,shutil,subprocess,sys,time
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).parent;OUT=HERE/'ROOT-ACTUAL-PUBLISHER-ADMISSION-1'
def ref(p):
 b=pathlib.Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,x):
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
ready=HERE/'PREPARED-SOURCE.json';assert ref(ready)['sha256']=='4efad3c4e35f0ce9599e3e022160969b9b083025df1c996549ab97809caa7ba4'
r=json.loads(ready.read_bytes())
for k in ('catalogue','normal_caller','normal_issuer','normal_producer_request','parent_manifest','child_manifest','profile'):
 assert ref(pathlib.Path(r[k]['path']))==r[k],k
review=HERE/'final-operation-review/OPERATION-REVIEW.json';assert ref(review)['sha256']=='cdc590cf8c99c4d731f1d75f056a2d981db0434c74878c31b91c94e02f889c83'
go=json.loads(review.read_bytes());assert set(go)=={'status','scope','proposal_sha256','driver_sha256','parent_manifest_sha256','child_manifest_sha256','native_release','native_currentfree','retire_operation_only'} and go['status']=='PASS_ACTUAL_INSTALL_ONLY' and go['scope']=='ROOT_CODE_INSTALL_ONLY' and go['native_release'] is False and go['native_currentfree'] is None and go['retire_operation_only'] is True
argv_path=HERE/'final-operation-review/FULL-ARGV.APPROVED.json';assert ref(argv_path)['sha256']=='92fe22e56a6d266ec128b9698c7fda9d7bb3a7687a22e39490e6d63a23f1d7df';argv=json.loads(argv_path.read_bytes())['producer_argv'];assert len(argv)==8 and argv[:3]==['/usr/bin/python3','-I','-B'] and argv[4:]==['--operation-review',str(review),'--operation-review-sha256',ref(review)['sha256']]
assert go['driver_sha256']==r['normal_caller']['sha256'] and go['parent_manifest_sha256']==r['parent_manifest']['sha256'] and go['child_manifest_sha256']==r['child_manifest']['sha256']
ret=HERE.parent.parent/'current81012-failed-recovery-1/phase-C-current-1/ROOT-CURRENT-RETIREMENT.FAILED-HOST-SCOPE-ONLY.json';assert ref(ret)['sha256']=='633f39c82b98fcaf424c45d13c4cbabf91153253d5ac576e959fe6f360d6ab92';prior=json.loads(ret.read_bytes());assert prior['current_HOST_payload_reserved_bytes_after']==0 and prior['current_HOST_jobs_after']==0 and prior['native_or_original_acceptance'] is False
assert not (HERE/'normal-operation-1/ROOT-EXEC-COMPLETION.ACTUAL.json').exists();OUT.mkdir(mode=0o700,exist_ok=False)
rows={}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  v=(p/'stat').read_text().rsplit(')',1)[1].split();rows[int(p.name)]={'pid':int(p.name),'ppid':int(v[1]),'birth':v[19],'state':v[0],'comm':(p/'comm').read_text().strip(),'rss_bytes':int(v[21])*os.sysconf('SC_PAGE_SIZE')}
 except FileNotFoundError:continue
roots={1824289:'56295798',1824291:'56295805',1824293:'56295812',1561218:'51981693',1561217:'51981691'}
for pid,birth in roots.items():assert rows[pid]['birth']==birth and rows[pid]['state'] not in ('Z','X','x')
family=set(roots);family.update(pid for pid,row in rows.items() if row['comm'] in ('codex','codex-code-mode','dockerd','containerd','containerd-shim') or row['comm'].startswith(('containerd-shim','qemu-system')))
while True:
 old=len(family);family.update(pid for pid,row in rows.items() if row['ppid'] in family)
 if len(family)==old:break
overhead=max(864333824,sum(rows[pid]['rss_bytes'] for pid in family if pid in rows));held=0;jobs=0;new=2147483648
available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;host=shutil.disk_usage(ROOT).free;scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch').free
assert held+overhead+new<=4*2**30 and jobs+1<=3 and available>=26*2**30 and host>=17*2**30 and scratch>=13*2**30
ps_argv=['/usr/bin/taskset','-c','6','/usr/bin/docker','ps','--no-trunc','--format','{{.ID}}'];ps=subprocess.run(ps_argv,cwd=str(ROOT),env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,check=True);assert ps.stdout.strip()==b'' and ps.stderr==b''
resource=OUT/'CURRENT-RESOURCE-AND-EXCLUSIVE-LANE.json';save(resource,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_ready':ref(ready),'exact_operation_review':ref(review),'actual_failed_HOST_scoped_retirement':ref(ret),'current_HOST_payload_bytes_before':held,'current_HOST_jobs_before':jobs,'new_current_family_bytes':new,'new_current_jobs':1,'all_controller_worker_overhead_bytes':overhead,'actual_rows':[rows[p] for p in sorted(family) if p in rows],'MemAvailable_bytes':available,'host_free_bytes':host,'scratch_free_bytes':scratch,'actual_running_container_check':{'argv':ps_argv,'exit':ps.returncode,'stdout':'','stderr':'','original_wait_and_streams_closed':True},'all_native12_source_globalUNKNOWN_and_original_raw_failures_preserved':True})
consumer=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/current-root-owner-1/current_account_snapshot.PROPOSED.py');owner=HERE/'normal-operation-1/CURRENT-ACTUAL-OWNER.json';assert ref(consumer)['sha256']=='fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6' and ref(owner)['sha256']=='a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'
ns={'__name__':'Root_reporting_normal_publication_current_account'};exec(compile(consumer.read_bytes(),str(consumer),'exec'),ns);state,usage,credit,observed=ns['current_account_snapshot'](json.loads(owner.read_bytes()));sys.path.insert(0,str(ROOT/'scripts'));import os_goal_guard_protocol
assert os_goal_guard_protocol.recovery_blocker(state,explicit_user=True) is None
account=OUT/'CURRENT-OWNER-ACCOUNT.PRIVATE.json';save(account,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'ACCEPTED','state':state,'usage':usage,'credit':credit,'independent_owner_ref':ref(owner)})
admission=OUT/'ROOT-CURRENT-ADMISSION.ACTUAL.json';save(admission,{'schema':'mckernel.Root-exact-reporting-normal-publisher-admission.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issued_utc_ns':time.time_ns(),'issued_monotonic_ns':time.monotonic_ns(),'invocation':'20261112T094452Z-12a4bea0','saved_Root':'01a18bc3-e072-7810-9426-75101b0856c0','same_Root_finite_credit_run_id':'7c6ef3604bfb4008a917bba8cfb6cfaa','operation_review':ref(review),'approved_argv':ref(argv_path),'actual_owner_account':ref(account),'actual_all_owner_resource_and_source_proof':ref(resource),'new_current_family_bytes':new,'new_current_jobs':1,'CPU':[6],'code_install_only':True,'new_native_release':False,'native_currentfree':None,'all_native12_source_global_UNKNOWNs_and_persistent_I_preserved':True,'retire_only_after_genuine_positive_current_full_Root_lease_client_capture_closure_and_independent_Q':True})
# Keep this pre-issuer admission receipt separate. Only the genuine reviewed issuer
# writes the normal three completion records to stdout; never trim/filter it.
os.sched_setaffinity(0,{6});os.execv(argv[0],argv)
