import datetime,fcntl,hashlib,json,os,pathlib,subprocess,time,sys
N=pathlib.Path(__file__).resolve().parent
release=N/'image-execution-release.json'
assert len(sys.argv)==2 and len(sys.argv[1])==64
assert hashlib.sha256(release.read_bytes()).hexdigest()==sys.argv[1]
d=json.loads(release.read_bytes()); assert hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()==d['dispatcher']['sha256']; qpath=pathlib.Path(d['request']['path']); assert hashlib.sha256(qpath.read_bytes()).hexdigest()==d['request']['sha256']; q=json.loads(qpath.read_bytes())
for name,sha in d['source_sha256'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==sha,name
for item in list(d['prerequisites'].values())+list(d['live_admission_required']['client_retirement'].values()):
 if not isinstance(item,dict):continue
 assert hashlib.sha256(pathlib.Path(item['path']).read_bytes()).hexdigest()==item['sha256'],item
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
published=json.loads(pathlib.Path(d['prerequisites']['publication']['path']).read_text());assert published['status']=='PASS' and published['commit']==published['fetched_commit']==d['publication_commit']
observed={r['path']:r for r in published['files']}
for row in d['publication_rows']:
 assert observed[row['repository_path']]['sha256']==row['sha256'] and observed[row['repository_path']]['bytes']==row['bytes']

mount=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-o','SOURCE,TARGET,UUID,MAJ:MIN','-T','/home/holden/mckernel-work/scratch'],text=True))['filesystems'][0]
assert mount=={'source':'/dev/loop36','target':'/home/holden/mckernel-work/scratch','uuid':d['scratch_binding']['uuid'],'maj:min':'7:36'},mount
assert pathlib.Path('/home/holden/mckernel-work/scratch').stat().st_dev==d['scratch_binding']['device']
source=pathlib.Path(q['source_root']).lstat(); assert (source.st_dev,source.st_ino,source.st_uid,source.st_gid,source.st_mode&4095)==tuple(d['live_admission_required']['source_identity'])
lock=pathlib.Path('/run/lock/mckernel-development.lock'); st=lock.stat(); assert (st.st_dev,st.st_ino,st.st_uid,st.st_gid)==(27,4,0,0)
with lock.open('r') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
spaces={}
for name,path in [('host',pathlib.Path('/home/holden')),('scratch',pathlib.Path('/home/holden/mckernel-work/scratch'))]:
 budget=d['live_admission_required']['storage']['per_filesystem'][name]
 s=os.statvfs(path);avail=s.f_bavail*s.f_frsize
 required=budget['floor_bytes']+budget['compiler_and_control_growth_bytes']+budget['postbuild_growth_bytes']+budget['emergency_reserve_bytes']
 spaces[name]={'available_bytes':avail,'required_bytes':required,'budget':budget,'margin_bytes':avail-required};assert avail>=required,spaces
mem={line.split(':')[0]:int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))};assert mem['MemAvailable']>=16*2**30,mem
state=json.loads(pathlib.Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes()); limits=state['last_rate_limits'];assert state.get('stop_reason') is None;assert limits['primary']['usedPercent']<97
paths=[q['lease_path'],q['common_exclusion_path'],q['attempt_root'],q['output_root'],d['guard_capture'],'/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock','/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18.json','/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json'];assert all(not os.path.lexists(x) for x in paths),[(x,os.path.lexists(x)) for x in paths]
assert not list(pathlib.Path(q['owner_evidence_root']).iterdir());assert not list(pathlib.Path(q['work_root']).iterdir())
head=subprocess.check_output(['/usr/bin/git','-C','/home/holden/mckernel','rev-parse','HEAD'],text=True).strip()
admission={'status':'PASS_FINAL_LIVE_ADMISSION','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'space':spaces,'memory':mem,'mount':mount,'head':head,'included_used_percent':limits['primary']['usedPercent'],'accepted_retirement':[d['live_admission_required']['client_retirement']['latest_actual_module_build_15clients']['sha256'],d['live_admission_required']['client_retirement']['prior_exact_image_terminal']['sha256']],'ownership_paths_absent':paths,'release_sha256':sys.argv[1]}
with (N/'image-final-live-admission.json').open('x') as f:json.dump(admission,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(admission,sort_keys=True),flush=True)
argv=['/home/holden/anaconda3/bin/python3','-B',str(N/'native_exact_scratch22_authority3_image_guard_corrected.py'),'--request',str(qpath),'--request-sha256',d['request']['sha256'],'--release',str(release),'--release-sha256',admission['release_sha256']]
t=time.monotonic()
with (N/'image-guard.stdout').open('xb') as out,(N/'image-guard.stderr').open('xb') as err:
 result=subprocess.run(argv,stdout=out,stderr=err,check=False)
status={'argv':argv,'returncode':result.returncode,'direct_child_joined':True,'no_automatic_retry':True,'elapsed_seconds':time.monotonic()-t,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (N/'image-guard.status.json').open('x') as f:json.dump(status,f,indent=2);f.write('\n')
print(json.dumps(status),flush=True)
# Ordinary postjoin readback only. Root/Docker terminal cleanup remains separate.
if result.returncode==0:
 proof_path=pathlib.Path(d['guard_capture'])/'guard-result.json';proof=json.loads(proof_path.read_bytes());assert proof['retired'] is True and proof['retained_for_separate_cleanup'] is True
 receipt=pathlib.Path(q['owner_evidence_root'])/'owner-receipt.json';assert hashlib.sha256(receipt.read_bytes()).hexdigest()==proof['owner_receipt_sha256']
 with lock.open('r') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 readback={'status':'PASS_ORDINARY_GUARD_POSTJOIN_READBACK_ONLY','guard_result_sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),'owner_receipt_sha256':proof['owner_receipt_sha256'],'container_id':proof['container_id'],'guard_direct_joined':True,'root27_4_reacquired_after_join':True,'common_shared_and_container_retained_for_separate_cleanup':True,'cleanup_authorized':False,'application_acceptance':False}
 with (N/'image-guard-postjoin-readback.json').open('x') as f:json.dump(readback,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(readback),flush=True)
raise SystemExit(result.returncode)
